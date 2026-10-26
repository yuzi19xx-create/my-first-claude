#!/usr/bin/env python3
"""英語動画 → 日本語字幕(.srt/.vtt/焼き込みmp4)を作るためのヘルパー。

サブコマンド:
  fetch       URLから動画を取得する(yt-dlp + node)
  transcribe  動画から英語音声を文字起こしし、segments.json を作る
  build       segments.json + translations.json から字幕ファイルを作る
              --burn を付けると字幕焼き込みmp4も作る

翻訳(英語→日本語)はこのスクリプトではやらない。Claudeが segments.json を読み、
文脈をまとめて訳した translations.json を書く。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

VENV_BIN = os.path.expanduser("~/.venvs/reel-transcribe/bin")
FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]
# 日本語の読みやすい速度の上限(文字/秒)。これを超える区間は表示時間を延ばす
MAX_CPS = 5.0
MIN_DURATION = 1.0


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    subprocess.run(cmd, check=True, **kw)


def cmd_fetch(a):
    os.makedirs(a.outdir, exist_ok=True)
    ytdlp = os.path.join(VENV_BIN, "yt-dlp")
    cmd = [ytdlp, "--js-runtimes", "node",
           "-f", "bv*[height<=720]+ba/b[height<=720]",
           "--merge-output-format", "mp4",
           "-o", os.path.join(a.outdir, "video.%(ext)s")]
    if a.cookies_from_browser:
        cmd += ["--cookies-from-browser", a.cookies_from_browser]
    run(cmd + [a.url])
    print(os.path.join(a.outdir, "video.mp4"))


def cmd_transcribe(a):
    os.makedirs(a.outdir, exist_ok=True)
    audio = os.path.join(a.outdir, "audio.mp3")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.video, "-vn",
         "-ac", "1", "-ar", "16000", audio])
    run([os.path.join(VENV_BIN, "whisper"), audio, "--language", a.language,
         "--model", a.model, "--output_format", "json", "--output_dir", a.outdir])
    raw = json.load(open(os.path.join(a.outdir, "audio.json"), encoding="utf-8"))
    segs = [{"id": i, "start": round(s["start"], 2), "end": round(s["end"], 2),
             "text": s["text"].strip()} for i, s in enumerate(raw["segments"])]
    out = os.path.join(a.outdir, "segments.json")
    json.dump(segs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


def load_translations(path, n):
    t = json.load(open(path, encoding="utf-8"))
    if isinstance(t, list):
        t = {str(i): v for i, v in enumerate(t)}
    missing = [i for i in range(n) if not str(t.get(str(i), "")).strip()]
    if missing:
        sys.exit(f"translations.json に訳が無いid: {missing}")
    return {int(k): v.strip() for k, v in t.items()}


def adjust_cues(segs, ja):
    """読める長さに表示時間を調整する。次の字幕とは重ねない。"""
    cues = []
    for i, s in enumerate(segs):
        text = ja[s["id"]]
        start, end = s["start"], s["end"]
        need = max(MIN_DURATION, len(text.replace("\n", "")) / MAX_CPS)
        limit = segs[i + 1]["start"] - 0.05 if i + 1 < len(segs) else end + need
        end = max(end, min(start + need, limit))
        cues.append({"start": start, "end": max(end, start + 0.3), "ja": text,
                     "en": s["text"]})
    return cues


def wrap_line(text, width):
    """1行がwidthを大きく超える場合だけ、句読点の位置を優先して折り返す。"""
    if len(text) <= width * 1.15:
        return [text]
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= width * 0.7 and ch in "、。,. ！？・":
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        while len(ln) > width * 1.3:
            out.append(ln[:width])
            ln = ln[width:]
        out.append(ln)
    return out


def wrap(text, width):
    """全角width文字を目安に折り返す。訳文中の改行は尊重し、長すぎる行だけ再分割する。"""
    out = []
    for ln in text.split("\n"):
        out += wrap_line(ln, width)
    return "\n".join(out)


def ts(sec, comma=True):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{',' if comma else '.'}{ms:03}"


def write_srt(cues, path, bilingual=False, width=20):
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            body = wrap(c["ja"], width)
            if bilingual:
                body += "\n" + c["en"]
            f.write(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{body}\n\n")


def write_vtt(cues, path, width=20):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for c in cues:
            f.write(f"{ts(c['start'], False)} --> {ts(c['end'], False)}\n"
                    f"{wrap(c['ja'], width)}\n\n")


def burn(video, cues, out, width, ypos=0.86):
    from PIL import Image, ImageDraw, ImageFont
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", video], text=True).strip()
    vw, vh = map(int, probe.split(","))
    font_path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if not font_path:
        sys.exit("日本語フォントが見つかりません(FONT_CANDIDATES を確認)")
    size = max(18, int(min(vw, vh) * 0.055))
    font = ImageFont.truetype(font_path, size)
    tmp = tempfile.mkdtemp(prefix="subs_")
    pngs = []
    for i, c in enumerate(cues):
        text = wrap(c["ja"], width)
        img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        box = d.multiline_textbbox((0, 0), text, font=font, align="center",
                                   spacing=size // 4, stroke_width=3)
        tw, th = box[2] - box[0], box[3] - box[1]
        x, y = (vw - tw) // 2, int(vh * ypos) - th
        pad = size // 3
        y = max(y, pad + 4)
        d.rounded_rectangle([x - pad, y - pad, x + tw + pad, y + th + pad],
                            radius=pad, fill=(0, 0, 0, 190))
        d.multiline_text((x - box[0], y - box[1]), text, font=font, fill="white",
                         align="center", spacing=size // 4, stroke_width=3,
                         stroke_fill="black")
        p = os.path.join(tmp, f"cue_{i:03}.png")
        img.save(p)
        pngs.append(p)
    inputs = ["-i", video]
    for p in pngs:
        inputs += ["-i", p]
    chain, last = [], "0:v"
    for i, c in enumerate(cues):
        nxt = f"v{i}"
        chain.append(f"[{last}][{i + 1}:v]overlay=0:0:"
                     f"enable='between(t,{c['start']:.2f},{c['end']:.2f})'[{nxt}]")
        last = nxt
    run(["ffmpeg", "-loglevel", "error", "-y", *inputs,
         "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?",
         "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "copy", out])


def cmd_build(a):
    segs = json.load(open(a.segments, encoding="utf-8"))
    ja = load_translations(a.translations, len(segs))
    cues = adjust_cues(segs, ja)
    os.makedirs(a.outdir, exist_ok=True)
    srt = os.path.join(a.outdir, "ja.srt")
    write_srt(cues, srt, width=a.width)
    write_srt(cues, os.path.join(a.outdir, "bilingual.srt"), bilingual=True, width=a.width)
    write_vtt(cues, os.path.join(a.outdir, "ja.vtt"), width=a.width)
    print(srt)
    if a.burn:
        out = os.path.join(a.outdir, "subtitled.mp4")
        burn(a.burn, cues, out, a.width, a.y)
        print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("url")
    f.add_argument("--outdir", required=True)
    f.add_argument("--cookies-from-browser", default=None,
                   help="bot判定で失敗した時だけ。例: chrome(キーチェーン許可が必要)")
    f.set_defaults(fn=cmd_fetch)
    t = sub.add_parser("transcribe")
    t.add_argument("video")
    t.add_argument("--outdir", required=True)
    t.add_argument("--model", default="small")
    t.add_argument("--language", default="English")
    t.set_defaults(fn=cmd_transcribe)
    b = sub.add_parser("build")
    b.add_argument("segments")
    b.add_argument("translations")
    b.add_argument("--outdir", required=True)
    b.add_argument("--burn", metavar="VIDEO", help="字幕焼き込みmp4も作る元動画")
    b.add_argument("--width", type=int, default=20,
                   help="1行の全角文字数(横動画20 / 縦動画12〜14)")
    b.add_argument("--y", type=float, default=0.86,
                   help="焼き込み字幕の下端の高さ(0=上端,1=下端)。元動画の下部に"
                        "英語テロップがある時は 0.2 など上側にずらす")
    b.set_defaults(fn=cmd_build)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
