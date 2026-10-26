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
- `transcribe` は `--model small` がデフォルト。CPUのみだと長い動画は数分かかるので、バックグラウンドで実行する。
- **small で足りることが多い**: 90秒の英語解説動画(はっきりした音声)で small と `medium` を比べたところ、差は「Login/Log in」のような表記程度で、製品名(Marketo, Salesforce)も small で正しく聞き取れていた。一方 medium はCPUのみで10分前後かかった。まず small で作り、聞き取りが怪しい時(訛り・早口・雑音・BGM)だけ `--model medium` を使う。
- medium は `~/.cache/whisper/medium.pt` が無い場合のみ約1.5GBのダウンロードが発生するので、その時はユーザーに伝えて許可を得てから。
- 製品名・専門用語が多い動画は `--prompt 'Marketo, Salesforce, API'` のように語を渡すと誤認識が減りうる(動画のタイトル・概要欄から拾う)。上の比較では効果は見えなかったので、smallで誤認識が出た時の対処として使う。
- 区間の境界(開始・終了時刻)はモデルで1秒ほどずれることがある。字幕のタイミングが気になる時は、その区間の音声を確認する。
- `--burn` は省略可。焼き込みは再エンコードが入るので、ユーザーが望んだ時だけ作る。
- `--y` は焼き込み字幕の下端の高さ(0=上端〜1=下端、デフォルト0.86=画面下)。**元動画の下部に英語テロップが焼き込まれている場合は、字幕が重なって読みにくくなるので `--y 0.3` 程度で上側に出す。** 最初に動画のフレームを1〜2枚(`ffmpeg -ss 10 -i video.mp4 -frames:v 1 f.png`)見て、既存の文字の位置を確認してから決める。
- **字幕が背景と重なって読みにくい時**: `--y 0.95 --cover-band 0.81,0.98` で画面下部に黒い帯を全編に敷き、その上に字幕を出す(英語テロップも隠れる)。字幕の文字は画面高さの4.5%。
- **黒帯を使わず背景を見せたい時**: 先に `erase` で元の英語テロップを消し、`--plain` で影+縁取りだけの字幕を焼く。
  ```bash
  $PY $S telop $W/video.mp4 --outdir $W --ymin 0.8 --ymax 0.95   # telops.json(UI等の誤検出は外す)
  $PY $S erase $W/video.mp4 $W/telops.json --outdir $W            # → $W/clean.mp4
  $PY $S build $W/segments.json $W/translations.json --outdir $W --burn $W/clean.mp4 --plain --y 0.95
  ```
  `erase` は各テロップの黒い縁取り(太い線のみ)から文字の範囲を検出し、その時間帯だけ `delogo` で周囲から埋める。操作画面の細い文字は無視する。背景が単色〜なだらかなグラデーションなら目立たないが、複雑な絵柄だとにじみが出る。`--pad`(既定16px)で消す範囲を広げられる。
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

## 動画内の英語テロップも訳す(任意・ユーザーが望んだ時だけ)

OCRはmacOS Vision(ローカル実行・トークン消費なし)。`pyobjc-framework-Vision pyobjc-framework-Quartz` が必要。

```bash
$PY $S telop $W/video.mp4 --outdir $W --ymin 0.6 --ymax 0.9 --min-text-height 0.03   # → $W/telops.json
# Claudeが $W/telop_translations.json を書く
$PY $S build $W/segments.json $W/translations.json --outdir $W --burn $W/video.mp4 \
   --telops $W/telops.json --telop-translations $W/telop_translations.json
```

- **OCRはテロップ以外も拾う**(操作画面のUI・ロゴ・写り込んだ文字)。必ず `--ymin/--ymax`(テロップの高さの帯)と `--min-text-height` で絞る。帯は動画のフレームを1枚見て決める。
- **トークン節約**: `telops.json` を丸ごと読まない。`head` で先頭数件と件数だけ確認する。テロップが話している内容とほぼ同じ字幕(カラオケ風)なら、音声の字幕で足りるので訳さずユーザーに伝える。訳すのは、音声に無い情報(見出し・数字・注意書き)だけ。
- 翻訳は、訳すテロップの `id` と `text` だけを短く抜き出して読み、`telop_translations.json` に書く(未翻訳のidがあるとbuildが止まる。訳さないものは `telops.json` から外す)。
- 訳さないテロップを `telops.json` から外すと `id` が飛ぶが、そのままでよい。`telop_translations.json` のキーは、残したテロップの `id` と同じにする(連番に振り直す必要はない)。
- 帯にUIの文字(操作画面のボタン名など)が混ざることがある。UIだけの行は外し、UIと混ざった行は、訳す側の文字だけを訳す(帯はUIの部分も隠す)。
- カラオケ風テロップ(1〜3語ずつ出る)をあえて上書きしたい場合は、`--fps 3` で細かく拾い、各断片を3〜10文字の短い訳にする。下部が日本語テロップで埋まるので、字幕は `--y 0.3` で上側に出す。
- 焼き込みは、元のテロップ位置を黒い帯で隠して日本語を重ねる。背景の絵柄は隠れる。

## 日本語音声で吹き替える(任意・ユーザーが望んだ時だけ)

`translations.json` をそのまま、macOSの音声合成(`say`)で読み上げる。ローカル実行なのでトークンは増えない。追加の翻訳も不要。

```bash
$PY $S dub $W/video.mp4 $W/segments.json $W/translations.json --outdir $W   # → $W/dubbed.mp4
```

- 字幕も同時に付けたい時は、`dub` の動画に焼き込み済みの `subtitled.mp4` を渡す(映像はコピーなので画質は落ちない)。
- **「方」の読み**: 人や「やり方」の「方」(例: 〜の方は、使い方は)は、吹き替え時に自動で「かた」に読み替える。「方法」「方向」「両方」「その方が」は「ほう」のまま。
- **読み方の指定**: 製品名などが英語読みされる時は `--reading Marketo=マルケト`(複数指定可)で、読み上げだけ読みを変える。字幕・テロップの表記は変わらない。ユーザーから読みを教わったら、この指定で反映する。
- **VOICEVOX(無料・ローカル、自然な声)**: アプリを起動した状態(`localhost:50021`)で `--engine voicevox --speaker 2`(2=四国めたん、3=ずんだもん、8=春日部つむぎ 等。一覧は `curl localhost:50021/speakers`)。`--speed` で話速。公開する場合は「VOICEVOX:話者名」のクレジット表記が必要(声ごとの規約を確認)。
- 元音声が邪魔な時は `--orig-volume 0.05`(0で完全に消す)。
- 声は `--voice`(デフォルト Kyoko。一覧は `say -v '?'`)、速さは `--rate`、元音声の音量は `--orig-volume`(デフォルト0.15)、吹き替えの音量は `--dub-volume`(デフォルト2.0)。
- 読み上げが次の発言に間に合わない区間は、最大 `--max-tempo`(1.5倍)まで速める。それでも食い込む区間は警告が出るので、その訳を短くして再実行する。
- 字幕用の訳は「読める速さ」で縮めてあるが、吹き替えは「聞ける速さ」が基準。自然な口調にしたい場合は、字幕と別に吹き替え用の訳を用意してもよい。
- **声の質を上げる**: macOSの「システム設定 → アクセシビリティ → 読み上げコンテンツ → システムの声 → 声を管理」で日本語の高品質版(拡張/Premium。Kyoko・Otoya・Eddy など)を追加し、`--voice` で名前を指定する。追加はユーザーの操作が必要(こちらから代行しない)。
- **自然さを上げる**: 吹き替えは字幕とは別に「話し言葉で、読み上げて自然な訳」を `dub_translations.json` として用意し、`dub` の第3引数に渡す。字幕用の訳(短縮・体言止め)をそのまま読むと不自然になりやすい。
- 合成音声なので、人の声の演技や感情は付かない。元の話者の声の再現(ボイスクローン)はこのスキルの範囲外。

## 日本語スライド資料HTMLを作る(任意・ユーザーが望んだ時だけ)

ウェビナー等で、英語スライドを日本語に直した画像を元画像と並べ、動画の再生位置と連動するHTMLを作る。スクリプトは `scripts/slides/`(`ocr.py` `render.py` `build.py` `man_example.py`)。作業ディレクトリに `s01.png`…(スライド切替フレーム)、`times.txt`(各フレームの秒)、`pages.py`(`PAGES=[(フレーム番号, 日本語タイトル, [本文行])]`、行頭「・」で箇条書き)、`full_segments.json` / `full_translations.json`(字幕の訳)を置いて使う。

1. **OCR**: `ocr.py`(pyobjc入りのvenv: `~/.venvs/reel-transcribe/bin/python`)。1024x576を2048x1152に拡大し、Apple Vision で文字ブロックを `B/ocr.json` に出す(id=`ページ-連番`, lines, x, y, w, h, lh, cen。左上原点)。
2. **訳**: `B/tr.py` に `TR={'ページ-連番':'日本語'}`(`\n`で改行、`''`で消去、書かないidは触らない)。画面操作のUIなど小さな文字は訳さなくてよい。
3. **描画**: `cd B && ~/.venvs/reel-transcribe/bin/python render.py 3 9 11`(番号省略で全ページ)→ `jaNN.jpg`。ブロックの範囲を、その中で最も多い背景色(量子化した最頻色)で塗りつぶし、ヒラギノで日本語を、枠に収まるまで縮めながら重ねる。numpyが要るのでvenvのpythonで実行する。
4. **HTML**: `python3 build.py` → `out/index.html`(元画像と日本語版を左右に並べ、発言の訳を折りたたみ表示、時刻クリックで動画シーク、再生に合わせて自動スクロール)。f-string内の `{` `}` は二重にする。`out/video.mp4` を置く。
   - HTMLの視聴機能(`build.py` に実装済み): 画像クリックで拡大表示(ライトボックス)/「動画を拡大」ボタンまたは動画のダブルクリックで動画を拡大し、右側に再生位置の日本語スライドを並べる(下のスライダーで動画とスライドの比率を変更、設定はlocalStorageに保存、初期は動画36%)/動画の再生位置をlocalStorageに保存し、開き直すと前回の続きから再生できる/動画を長押し中(0.3秒以上)だけ2倍速(黄色い枠で表示、再生バー付近は対象外)。localStorageはtry/catchで囲んであり、使えなくても動く。
   - **マインドマップ(復習用)**: `python3 mindmap.py` → `out/mindmap.html`(別ファイル)。章 → 論点 → 小項目の折りたたみツリーで、各論点に時刻リンクが付く。リンクは `index.html#t=秒` で、開くと動画をその位置へシークして再生する。`index.html` のヘッダーからもリンクされている。章立て・内容は `mindmap.py` 冒頭の `D`(章, 開始秒, [(論点, 開始秒, [小項目])])を、スライドのタイトル・発言の訳・`times.txt` の各ページ開始時刻から作り直す。
5. **確認はページごとに画像を見る**(`jaNN.jpg` を読む)。直すのは次の2通り:
   - OCRの値の修正: `ocr.json` の x/y/h/lh を直接直す(行ごとに開始位置や文字高がばらつく場合は、x・lhを揃える。例: 箇条書き4行のx=410, lh=48)。
   - **手動上書き `man.py`**: ブロックが混ざる・割れる・・とずれる表や囲み図は、`MAN[ページ]=dict(erase=[矩形], texts=[(x,y,最大幅,文,サイズ,太さ,色,行送り)], lft=[(x,中心y,文,サイズ,太さ,色,最大幅)], ctr=[(中心x,中心y,文,...)], fill=[(色,矩形)])` で、消す範囲と文字を座標で指定する。元画像の・やチェック印は残し、文字だけを元の行位置に書き直す。実例は `man_example.py`。座標は2048x1152基準(スクリーンショット表示が2000幅なら×1.024)。
6. **品質の勘所**: 小さい文字や図中の文字は訳し漏れが出やすい。翻訳もれ(英語の残り)、文字の重なり、・や印との位置ずれ、不要な背景色の塗り、文字が画像と同化して読めない、の5点を見る。長文は同じ意味で短くして収める。
7. **作成後は必ず元画像と見比べる**(`check.py [ページ]` で・や□の消え漏れを検出。自動修正はしない)。よくある原因と対処:
   - OCRが見出しと本文を1ブロックに混ぜる → そのページは `ocr.json` のブロックを空にして `man.py` の `lft`/`texts` で描き直す。
   - ・やチェックボックスをOCRが文字として拾わず、消去範囲に入って消える → `texts` の行頭に「・」を足す、または `fill` で描き直す。
   - `erase` が埋め込みスクリーンショットやイラストまで消す → 矩形を文字領域だけに絞る。
   - 描画順は erase→fill→lft→ctr→texts。fill は文字より先に描かれる。
   - ブロック個別の上書きは `ocr.json` の `mw`(最大幅) `wt`(太さ) `sz`(サイズ) `col`(文字色) `bgc`(背景色)。
   - 色は元画像の色を使う。元が赤でない文字を赤にしない。元が太字なら太字、見出しと本文の構造も保つ。

## 確認と報告

- `build` が `translations.json に訳が無いid` で止まったら、足りないidを訳して再実行する。
- 仕上がりを確認する: `ja.srt` の先頭と末尾を読み、時刻と内容が合っているか見る。焼き込み動画は、数点のフレームを切り出して(`ffmpeg -ss <秒> -i subtitled.mp4 -frames:v 1 out.png`)字幕の位置・文字の欠けを確認する。
- 報告には、字幕の枚数、動画の長さ、聞き取りに自信が無かった箇所、表示時間を延ばした区間があればその旨を含める。
- 動画や字幕は私的利用の範囲で。他人の動画を翻訳して再公開する場合は権利の確認が必要なので、そのような用途ならユーザーに一言伝える。
