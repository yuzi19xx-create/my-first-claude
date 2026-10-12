#!/usr/bin/env python3
"""
Instagramリール等の動画を取得し、
  - 音声のナレーションをWhisperで文字起こし
  - 映像のテロップ(画面表示テキスト)をOCRで抽出
した上で、時間軸に沿って統合表示するツール。

使い方:
  source ~/.venvs/reel-transcribe/bin/activate
  python3 ~/reel-tools/transcribe_reel.py <動画URL> [--model small] [--fps 1] [--outdir /tmp/xxx]

出力:
  - 標準出力に読みやすいプレビューを表示(種別は「音声」「映像」の文字で明示)
  - <outdir>/timeline.csv にスプレッドシートへ貼り付け可能な表形式で保存
    列: 開始(秒) / 終了(秒) / 種別 / リンクID / 内容
    「リンクID」が同じ行は、時間的に重なっている(=同じ場面を指している可能性が高い)音声と映像。
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass

import Quartz
import Vision
from Foundation import NSURL


@dataclass
class Event:
    start: float
    end: float
    kind: str  # "音声" or "映像テロップ"
    text: str


def run(cmd, **kwargs):
    return subprocess.run(
        cmd, check=True, capture_output=True, text=True, errors="replace", **kwargs
    )


def download_video(url: str, outdir: str) -> str:
    video_path = os.path.join(outdir, "video.mp4")
    run(["yt-dlp", "-f", "mp4/best", "-o", video_path, url])
    if not os.path.exists(video_path):
        # yt-dlp may have appended a different extension; find it
        for f in os.listdir(outdir):
            if f.startswith("video."):
                return os.path.join(outdir, f)
        raise FileNotFoundError("video download failed")
    return video_path


def fetch_caption(url: str) -> str:
    """投稿本文(キャプション)をyt-dlpのメタデータから取得する。"""
    result = run(["yt-dlp", "--skip-download", "--print", "description", url])
    return result.stdout.strip()


def fetch_video_stats(url: str) -> dict:
    """yt-dlpのメタデータから取得できる範囲の統計情報を取得する。

    再生数・フォロワー数・投稿数はyt-dlpのInstagram抽出では取得できないため、
    ここでは空欄にしておき、ブラウザ等で調べた値を後から埋める想定。
    """
    result = run([
        "yt-dlp", "--skip-download", "-j", url,
    ])
    data = json.loads(result.stdout)
    upload_date = data.get("upload_date")  # "YYYYMMDD" 形式
    post_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}" if upload_date else None
    return {
        "account_name": data.get("uploader") or "",
        "account_handle": data.get("channel") or data.get("uploader_id") or "",
        "like_count": data.get("like_count"),
        "comment_count": data.get("comment_count"),
        "post_date": post_date,
        "view_count": None,      # ブラウザ等で別途取得
        "follower_count": None,  # ブラウザ等で別途取得
        "post_count": None,      # ブラウザ等で別途取得
    }


def extract_audio(video_path: str, outdir: str) -> str:
    audio_path = os.path.join(outdir, "audio.mp3")
    run(["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", audio_path])
    return audio_path


def transcribe_audio(audio_path: str, outdir: str, model: str, language: str) -> list[Event]:
    run([
        "whisper", audio_path,
        "--language", language,
        "--model", model,
        "--output_format", "json",
        "--output_dir", outdir,
    ])
    json_path = os.path.splitext(audio_path)[0] + ".json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    events = []
    for seg in data.get("segments", []):
        text = seg["text"].strip()
        if text:
            events.append(Event(start=seg["start"], end=seg["end"], kind="音声", text=text))
    return events


def extract_frames(video_path: str, outdir: str, fps: float) -> str:
    frames_dir = os.path.join(outdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={fps}",
        os.path.join(frames_dir, "frame_%04d.png"),
    ])
    return frames_dir


def normalize_text(t: str) -> str:
    t = re.sub(r"\s+", "", t)
    return t.strip()


def ocr_image(path: str, languages=("ja", "en"), min_height_ratio: float = 0.025) -> str:
    """1枚の画像から文字を抽出する(macOS Vision framework)。

    実際の字幕・テロップは背景の装飾グラフィック(AIっぽい雰囲気を出すための
    ホログラム風UIなど)の文字より大きく表示されることが多いので、
    画面全体に対する文字の高さの比率(boundingBoxのheight)が小さすぎるものは
    装飾ノイズとみなして除外する。
    """
    url = NSURL.fileURLWithPath_(path)
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(list(languages))
    request.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    ok, _err = handler.performRequests_error_([request], None)
    if not ok:
        return ""
    lines = []
    for obs in request.results():
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        bbox = obs.boundingBox()
        if bbox.size.height < min_height_ratio:
            continue  # 小さすぎる文字 = 背景装飾グラフィックのノイズとみなす
        lines.append(str(cand[0].string()))
    return "\n".join(lines)


def ocr_frames(frames_dir: str, fps: float, min_height_ratio: float = 0.025) -> list[Event]:
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
    raw = []  # (time, normalized_text, original_text)
    for f in files:
        idx = int(re.search(r"(\d+)", f).group(1))
        t = (idx - 1) / fps
        path = os.path.join(frames_dir, f)
        text = ocr_image(path, min_height_ratio=min_height_ratio)
        raw.append((t, normalize_text(text), text))

    # consecutive frames with the same normalized text -> merge into one block
    events: list[Event] = []
    i = 0
    frame_dt = 1.0 / fps
    while i < len(raw):
        t_start, norm, orig = raw[i]
        if not norm:
            i += 1
            continue
        j = i + 1
        t_end = t_start + frame_dt
        while j < len(raw) and raw[j][1] == norm:
            t_end = raw[j][0] + frame_dt
            j += 1
        events.append(Event(start=t_start, end=t_end, kind="映像テロップ", text=orig.replace("\n", " / ")))
        i = j
    return events


def fmt_time(s: float) -> str:
    return f"{s:.1f}"


def assign_links(audio_events: list[Event], telop_events: list[Event]) -> dict[int, int]:
    """各イベントのidに、対応する音声区間の連番(リンクID)を割り当てる。
    音声と時間帯が重なる映像テロップは、その音声と「同じ内容を扱っている」と推定してリンクさせる。
    重ならないテロップ(音声の合間の場面)はリンクなし(空欄)とする。
    """
    link_of: dict[int, int] = {}
    for a_idx, a in enumerate(audio_events):
        link_of[id(a)] = a_idx
        for t in telop_events:
            overlap = min(a.end, t.end) - max(a.start, t.start)
            if overlap > 0:
                # 既に他の音声とリンク済みなら先に見つかった方を優先(最初の重なりを採用)
                prev = link_of.get(id(t))
                if prev is None:
                    link_of[id(t)] = a_idx
    return link_of


# 「音声」「映像」は見た瞬間に区別できるよう、色や似た絵文字ではなく
# 文字そのもの(種別列)で区別する。行頭記号もあえて非対称な形にしておく。
ROW_MARK = {"音声": "＝", "映像テロップ": "・"}


def build_rows(audio_events: list[Event], telop_events: list[Event]) -> list[dict]:
    """スプレッドシートに貼り付けられる行データ(dictのリスト)を作る。

    「内容(整文)」は自動では元データと同じ値になる。OCR/音声認識の生データは
    誤字・断片化が多いので、実際にはこの列を後から(Claudeが)書いてある文言を
    最優先にしつつ意味が通じる日本語に整えて上書きすることを想定している。
    """
    link_of = assign_links(audio_events, telop_events)
    all_events = sorted(audio_events + telop_events, key=lambda e: e.start)

    rows = []
    for e in all_events:
        link_id = link_of.get(id(e))
        rows.append({
            "開始(秒)": fmt_time(e.start),
            "終了(秒)": fmt_time(e.end),
            "種別": "音声" if e.kind == "音声" else "映像",
            "リンクID": "" if link_id is None else f"L{link_id + 1}",
            "内容(元データ)": e.text,
            "内容(整文)": e.text,
        })
    return rows


CSV_FIELDS = ["開始(秒)", "終了(秒)", "種別", "リンクID", "内容(元データ)", "内容(整文)"]


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(
    rows: list[dict],
    path: str,
    caption: str = "",
    stats: dict | None = None,
    thumbnail_path: str | None = None,
    url: str = "",
    video_title: str | None = None,
) -> None:
    """書式付きのExcelファイルを作る。

    上部に「音声だけの流れ」セクションを置く(音声を通して読むと動画全体の
    流れがつかめるため)。その下に、音声+映像の全体タイムラインを続ける。
    - 音声の行は薄い黄色で塗る(一瞬で音声/映像がわかるように)
    - 全体タイムラインでは、リンクIDが変わる境目に太い罫線を引いて
      場面のまとまりを見た目でも区切る
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    def sanitize_sheet_name(name: str, maxlen: int = 31) -> str:
        for ch in "\\/?*[]:":
            name = name.replace(ch, "")
        name = name.strip() or "timeline"
        if len(name) <= maxlen:
            return name
        truncated = name[:maxlen]
        # 単語の途中で切れないよう、直近の助詞・区切り記号まで戻ってから切る
        boundary_chars = "、。！？のがをにへとではも"
        for i in range(len(truncated) - 1, 0, -1):
            if truncated[i] in boundary_chars:
                return truncated[: i + 1]
        return truncated  # 区切りが見つからない場合はそのまま切る

    # シート名・動画タイトルは、呼び出し側が video_title を渡せばそれを使う
    # (表紙/サムネイルに大きく表示されているタイトル文字がある場合はそちらを
    # 優先すべきなので、呼び出し側で判断してもらう)。指定が無ければ、
    # 最初の音声(L1)の整文から自動生成する。
    # 整文には判断根拠の注記(例:「(テロップで確認済み)」)が末尾に括弧書きで
    # 付くことがあるため、タイトル用にはそれを取り除く(表内のセルには残す)。
    import re

    def strip_trailing_note(text: str) -> str:
        return re.sub(r"[(（][^()（）]*[)）]\s*$", "", text).strip()

    if video_title is None:
        audio_rows_all = [r for r in rows if r["種別"] == "音声"]
        video_title = strip_trailing_note(audio_rows_all[0]["内容(整文)"]) if audio_rows_all else "タイムライン"

    wb = Workbook()
    ws = wb.active
    ws.title = sanitize_sheet_name(video_title)

    # 1行目: 動画タイトル、2行目: 動画URL(ラベルなし、URLのみ)、3行目: 空行(その後にアカウントハンドル以降が続く)
    ws.append([f"動画タイトル：{video_title}"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)
    if url:
        ws.append([url])
    ws.append([])  # 区切りの空行

    # --- 動画・プロフィール情報 ---
    # 再生数・フォロワー数・投稿数はyt-dlpでは取得できないため、statsに値が無ければ空欄
    # (ブラウザ等で調べた値を後から埋める、または手入力する想定)
    s = stats or {}
    number_format = "#,##0"

    def append_count(label: str, value) -> int:
        ws.append([label, value])
        row = ws.max_row
        ws.cell(row=row, column=2).number_format = number_format
        return row

    def append_ratio(label: str, numerator_row: int, denominator_row: int, ratio_format: str | None = None) -> None:
        ws.append([label, f"=B{numerator_row}/B{denominator_row}"])
        cell = ws.cell(row=ws.max_row, column=2)
        cell.font = Font(color="FF0000")
        if ratio_format:
            cell.number_format = ratio_format

    ws.append(["アカウントハンドル", s.get("account_handle", "")])
    ws.append(["アカウント表示名", s.get("account_name", "")])
    follower_row = append_count("フォロワー", s.get("follower_count"))
    append_count("投稿数", s.get("post_count"))
    ws.append([])  # （リール単体）の前に1行あける
    ws.append(["（リール単体）"])
    ws.append(["投稿日", s.get("post_date", "")])
    view_row = append_count("再生数", s.get("view_count"))
    append_ratio("再生数/フォロワー数", view_row, follower_row, ratio_format="0.0")
    like_row = append_count("いいね数", s.get("like_count"))
    append_ratio("いいね数/フォロワー数", like_row, follower_row, ratio_format="0.0%")
    comment_row = append_count("コメント数", s.get("comment_count"))
    append_ratio("コメント数/フォロワー数", comment_row, follower_row, ratio_format="0.00%")
    ws.append([])  # 区切りの空行

    # 一覧(グリッド)に表示される、この投稿のサムネイル画像を貼り付ける
    if thumbnail_path and os.path.exists(thumbnail_path):
        from openpyxl.drawing.image import Image as XLImage

        img = XLImage(thumbnail_path)
        aspect = img.height / img.width
        target_width = 160
        img.width = target_width
        img.height = int(target_width * aspect)
        ws.add_image(img, "D3")

    yellow_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    thin = Side(style="thin", color="BBBBBB")
    thick = Side(style="thick", color="333333")
    wrap_top = Alignment(wrap_text=True, vertical="top")
    ncols = len(CSV_FIELDS)

    def write_header(title: str):
        ws.append([title])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=13)
        ws.append(CSV_FIELDS)
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)

    CHARS_PER_LINE = 30  # 500px幅で1行に収まる目安の文字数(全角。以前の60は過大評価だった)
    LINE_HEIGHT_PT = 15  # 1行あたりの高さ(pt)
    LINE_BUFFER = 1  # 見積もり誤差を吸収するための余白(行数)

    def write_data_row(r: dict, border_top):
        ws.append([r["開始(秒)"], r["終了(秒)"], r["種別"], r["リンクID"], r["内容(元データ)"], r["内容(整文)"]])
        row_cells = ws[ws.max_row]
        if r["種別"] == "音声":
            for cell in row_cells:
                cell.fill = yellow_fill
        for cell in row_cells:
            cell.border = Border(top=border_top, bottom=thin, left=thin, right=thin)
        # E列(内容(元データ))・F列(内容(整文))は折り返して上揃え
        row_cells[4].alignment = wrap_top
        row_cells[5].alignment = wrap_top
        # 折り返した結果、文字が隠れないように行の高さを内容量に応じて広げる
        longest = max(len(r["内容(元データ)"]), len(r["内容(整文)"]))
        lines = max(1, -(-longest // CHARS_PER_LINE)) + LINE_BUFFER  # ceil division + 余白
        ws.row_dimensions[ws.max_row].height = lines * LINE_HEIGHT_PT
        return row_cells

    # --- セクション1: 音声だけの流れ ---
    write_header("▼ 音声(ナレーション)の流れ ※これだけ読むと動画全体の流れがつかめます")
    header_row = ws.max_row  # 内容(整文)=F列の見出しがあるこの行に、G列のキャプション見出しを揃える
    audio_rows = [r for r in rows if r["種別"] == "音声"]
    for r in audio_rows:
        write_data_row(r, thin)

    ws.append([])  # 区切りの空行

    # --- セクション2: 音声+映像の全体タイムライン ---
    write_header("▼ 全体タイムライン(音声+映像テロップ)")
    prev_link = None
    for r in rows:
        is_new_group = r["リンクID"] != prev_link
        row_cells = write_data_row(r, thick if is_new_group else thin)
        prev_link = r["リンクID"]
    if rows:
        for cell in ws[ws.max_row]:
            cell.border = Border(top=cell.border.top, bottom=thick, left=thin, right=thin)

    # --- G列: キャプション(投稿本文)。内容(整文)=F列の見出しと同じ行に見出しを置き、
    #     その次の行(データの1行目=内容(整文)の隣)から改行ごとに1行ずつ、重複なく配置 ---
    ws.cell(row=header_row, column=7, value="キャプション").font = Font(bold=True)
    if caption:
        caption_lines = [ln.strip() for ln in caption.splitlines() if ln.strip()]
        for i, line in enumerate(caption_lines):
            cell = ws.cell(row=header_row + 1 + i, column=7, value=line)
            cell.alignment = wrap_top

    # 列幅はpx指定をExcelの幅単位に変換(width単位 = (px - 5) / 7 の近似式)
    widths_px = {"A": 90, "B": 90, "C": 60, "D": 70, "E": 500, "F": 500, "G": 300}
    for col, px in widths_px.items():
        ws.column_dimensions[col].width = (px - 5) / 7

    wb.save(path)


def build_preview_text(rows: list[dict]) -> str:
    """チャット等で読みやすいプレーンテキスト版(種別を文字で明示)。"""
    lines = []
    for r in rows:
        mark = ROW_MARK["音声" if r["種別"] == "音声" else "映像テロップ"]
        link = f"[{r['リンクID']}] " if r["リンクID"] else ""
        lines.append(
            f"{mark}[{r['種別']}] {link}{r['開始(秒)']}秒〜{r['終了(秒)']}秒: {r['内容(整文)']}"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default="")
    ap.add_argument("--video", default=None, help="取得済みのローカル動画(画面収録など)を使う。指定時はダウンロードとキャプション取得を省略")
    ap.add_argument("--model", default="small", help="Whisperモデル (tiny/base/small/medium/large)")
    ap.add_argument("--language", default="Japanese")
    ap.add_argument("--fps", type=float, default=1.0, help="テロップ抽出のフレームレート(1秒あたり何枚)")
    ap.add_argument(
        "--min-text-height", type=float, default=0.025,
        help="この比率(画面高さに対する文字の高さ)より小さい文字は背景装飾ノイズとみなして除外",
    )
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    if not args.url and not args.video:
        ap.error("url か --video のどちらかを指定してください")
    outdir = args.outdir or os.path.join("/tmp", "reel_transcribe_" + str(abs(hash(args.url or args.video)) % 100000))
    os.makedirs(outdir, exist_ok=True)

    if args.video:
        print(f"[1/5] ローカル動画を使用: {args.video}", file=sys.stderr)
        video_path = os.path.abspath(args.video)
    else:
        print(f"[1/5] 動画をダウンロード中... -> {outdir}", file=sys.stderr)
        video_path = download_video(args.url, outdir)

    print("[2/5] 音声を抽出中...", file=sys.stderr)
    audio_path = extract_audio(video_path, outdir)

    print("[3/5] 音声を文字起こし中(Whisper)...", file=sys.stderr)
    audio_events = transcribe_audio(audio_path, outdir, args.model, args.language)

    print("[4/5] フレームを抽出中...", file=sys.stderr)
    frames_dir = extract_frames(video_path, outdir, args.fps)

    print("[5/5] 映像テロップをOCR中...", file=sys.stderr)
    telop_events = ocr_frames(frames_dir, args.fps, min_height_ratio=args.min_text_height)

    rows = build_rows(audio_events, telop_events)

    if args.url:
        print("[+] キャプションを取得中...", file=sys.stderr)
        caption = fetch_caption(args.url)
    else:
        caption = ""

    csv_path = os.path.join(outdir, "timeline.csv")
    write_csv(rows, csv_path)

    xlsx_path = os.path.join(outdir, "timeline.xlsx")
    write_xlsx(rows, xlsx_path, caption=caption, url=args.url)

    print(build_preview_text(rows))
    print(f"\n(CSV保存先: {csv_path})", file=sys.stderr)
    print(f"(書式付きExcel保存先: {xlsx_path})", file=sys.stderr)


if __name__ == "__main__":
    main()
