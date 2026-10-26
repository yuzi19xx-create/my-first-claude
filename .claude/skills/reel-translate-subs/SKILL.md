---
name: reel-translate-subs
description: Turn an English video (YouTube URL, Instagram reel URL, or a local mp4) into Japanese subtitles synced to the original timing — outputs .srt/.vtt files and, on request, an mp4 with the Japanese subtitles burned in. Use whenever the user asks to translate a video into Japanese, add Japanese subtitles, or watch an English video in Japanese. Not for analysing a reel's narration/telop into Excel (that is reel-transcribe).
---

# 英語動画 → 日本語字幕スキル

英語の音声を文字起こしし、各発言の開始・終了時刻を保ったまま日本語に訳して、字幕ファイルにする。

`reel-transcribe`(音声+テロップを分析してExcelにする)とは目的が違う。こちらは「視聴用の字幕」を作る。

## 全体の流れ

1. 動画を用意する(`fetch`、またはローカルmp4をそのまま使う)
2. 英語を文字起こしして `segments.json` を作る(`transcribe`)
3. **Claudeが `segments.json` を読み、日本語訳を `translations.json` に書く**(下記「翻訳の方法」)
4. `build` で `ja.srt` / `bilingual.srt` / `ja.vtt` を作る。希望があれば `--burn` で焼き込みmp4も作る
5. 出力先とファイルをユーザーに伝え、`SendUserFile` で送る

作業ディレクトリはプロジェクト外(スクラッチパッドなど)に置く。

## セットアップ(初回のみ)

`reel-transcribe` と同じvenvを使う。無ければ作る。

```bash
brew install ffmpeg node
python3 -m venv ~/.venvs/reel-transcribe
~/.venvs/reel-transcribe/bin/pip install yt-dlp yt-dlp-ejs openai-whisper pillow
```

- YouTubeの取得にはJavaScriptランタイム(`node`)と `yt-dlp-ejs` が必要。無いと「Sign in to confirm you're not a bot」「n challenge solving failed」で失敗する。`fetch` は `--js-runtimes node` を自動で付ける。
- ffmpegは字幕フィルタ(libass/freetype)が入っていない版が多い。そのため焼き込みはPillowで字幕画像を作ってoverlayする方式にしてある。ffmpegの `subtitles=` フィルタは使えない前提で考える。

## 実行方法

以下 `$S` はこのスキルの `scripts/make_subs.py`、`$W` は作業ディレクトリ。

```bash
PY=~/.venvs/reel-transcribe/bin/python
$PY $S fetch "<URL>" --outdir $W                 # → $W/video.mp4
$PY $S transcribe $W/video.mp4 --outdir $W       # → $W/segments.json
# ここでClaudeが $W/translations.json を書く
$PY $S build $W/segments.json $W/translations.json --outdir $W --burn $W/video.mp4
```

- `fetch` がボット判定で失敗した場合のみ、ユーザーに説明して許可を得てから `--cookies-from-browser chrome` を付ける。macOSのキーチェーン許可ダイアログがユーザーの画面に出て、パスワード入力が必要になる(代行できない。「許可」を押してもらい、「常に許可」は避けるよう伝える)。まずは付けずに試す。
- `transcribe` は `--model small` がデフォルト。CPUのみだと長い動画は数分かかるので、バックグラウンドで実行する。聞き取りが怪しい時は `--model medium`。
- `--burn` は省略可。焼き込みは再エンコードが入るので、ユーザーが望んだ時だけ作る。
- `--y` は焼き込み字幕の下端の高さ(0=上端〜1=下端、デフォルト0.86=画面下)。**元動画の下部に英語テロップが焼き込まれている場合は、字幕が重なって読みにくくなるので `--y 0.3` 程度で上側に出す。** 最初に動画のフレームを1〜2枚(`ffmpeg -ss 10 -i video.mp4 -frames:v 1 f.png`)見て、既存の文字の位置を確認してから決める。
- `--width` は1行の全角文字数。横動画は20(デフォルト)、縦動画(リール)は12〜14。

出力:

| ファイル | 内容 |
|---|---|
| `ja.srt` | 日本語字幕(多くのプレーヤーで読める) |
| `bilingual.srt` | 日本語+英語の2段字幕 |
| `ja.vtt` | ブラウザの `<track>` 用 |
| `subtitled.mp4` | 日本語字幕を焼き込んだ動画(`--burn` 時のみ) |

## 翻訳の方法(最も重要な工程)

`segments.json` は `[{id, start, end, text}, ...]`。Whisperの区間は文の途中で切れていることがある。区間ごとに別々に訳さず、**全体を通して読み、文脈をまとめて訳してから、区間に割り振る**。

1. 最後まで通読して、話題・用語・話者の口調を把握する。
2. 区間ごとの訳を作る。文が複数区間にまたがる場合は、日本語として自然な位置で区切って各区間に分ける。区間が追加・削除されることはない(idは必ず全部埋める)。
3. 1区間あたりの文字数は、**区間の秒数 × 5文字**を目安にする(日本語字幕の読める速度の上限)。超える場合は要約して縮める。逆に長く表示できる区間(次の発言まで間がある)は少し余裕がある。
4. 固有名詞・製品名(例: Salesforce, Marketo)は原語のままにするか、一般的なカタカナ表記にする。聞き取りが怪しい固有名詞は、音声認識の誤りを疑って文脈から判断し、自信が無ければ原語のままにしてユーザーに伝える。
5. 字幕は話し言葉の短い文にする。「〜です」「〜します」を基本に、体言止めや説明的な長文は避ける。
6. 創作・補足は禁止。原文に無い情報を足さない。意訳は意味が変わらない範囲にとどめる。

`translations.json` の形式(idをキーにした辞書、または区間順の文字列配列):

```json
{"0": "こんにちは。今日はMarketoとSalesforceの連携を説明します。", "1": "..."}
```

1区間内で改行したい場合は `\n` を入れる(入れなければ `--width` で自動折り返し)。

## 確認と報告

- `build` が `translations.json に訳が無いid` で止まったら、足りないidを訳して再実行する。
- 仕上がりを確認する: `ja.srt` の先頭と末尾を読み、時刻と内容が合っているか見る。焼き込み動画は、数点のフレームを切り出して(`ffmpeg -ss <秒> -i subtitled.mp4 -frames:v 1 out.png`)字幕の位置・文字の欠けを確認する。
- 報告には、字幕の枚数、動画の長さ、聞き取りに自信が無かった箇所、表示時間を延ばした区間があればその旨を含める。
- 動画や字幕は私的利用の範囲で。他人の動画を翻訳して再公開する場合は権利の確認が必要なので、そのような用途ならユーザーに一言伝える。
