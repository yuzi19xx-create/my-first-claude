#!/bin/bash
# 画面+BlackHole音声を録画する(yt-dlpで取得できないリール用のフォールバック)
#
# 使い方: record_screen.sh <出力mp4> <録画秒数> [画面番号(既定0)] [crop=幅:高さ:x:y]
#   例: record_screen.sh /tmp/reel_x/video.mp4 40
#
# 事前準備: BlackHole 2ch のインストールと、Audio MIDI設定での
#           複数出力装置「リール録音用」(BlackHole 2ch + スピーカー)の作成。
# 録画中は出力先を「リール録音用」に切り替え、終了時(失敗・中断時も)元に戻す。
# 注意: 画面収録の権限(システム設定 > プライバシーとセキュリティ > 画面収録)が
#       実行元アプリ(ターミナル/Claude)に必要。

set -u
OUT="${1:?出力mp4を指定してください}"
DUR="${2:?録画秒数を指定してください}"
SCREEN="${3:-0}"
CROP="${4:-}"; CROP="${CROP#crop=}"
DEVICE="${MULTI_OUTPUT_NAME:-リール録音用}"

command -v SwitchAudioSource >/dev/null || { echo "SwitchAudioSource が未インストール (brew install switchaudio-osx)" >&2; exit 1; }
SwitchAudioSource -a -t output | grep -qx "$DEVICE" || { echo "複数出力装置「$DEVICE」が見つかりません" >&2; exit 1; }

LIST=$(ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1)
VIDX=$(echo "$LIST" | grep "Capture screen $SCREEN" | sed -E 's/.*\[([0-9]+)\] Capture screen.*/\1/' | head -1)
AIDX=$(echo "$LIST" | sed -n '/audio devices/,$p' | grep "BlackHole 2ch" | sed -E 's/.*\[([0-9]+)\] BlackHole.*/\1/' | head -1)
[ -n "$VIDX" ] || { echo "Capture screen $SCREEN が見つかりません" >&2; exit 1; }
[ -n "$AIDX" ] || { echo "BlackHole 2ch が見つかりません(再起動したか確認)" >&2; exit 1; }

ORIG=$(SwitchAudioSource -c -t output)
restore() { SwitchAudioSource -t output -s "$ORIG" >/dev/null 2>&1; echo "出力先を元に戻しました: $ORIG" >&2; }
trap restore EXIT INT TERM

SwitchAudioSource -t output -s "$DEVICE" >/dev/null || exit 1

VF="scale=trunc(iw/2)*2:trunc(ih/2)*2"
[ -n "$CROP" ] && VF="crop=$CROP,$VF"

mkdir -p "$(dirname "$OUT")"
echo "録画開始: ${DUR}秒 (画面$SCREEN)。この間にリールを再生してください。" >&2
ffmpeg -hide_banner -loglevel error -y \
  -f avfoundation -framerate 30 -capture_cursor 0 -i "$VIDX:$AIDX" \
  -t "$DUR" -vf "$VF" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -b:a 160k "$OUT"
RC=$?

# 無音チェック(最大音量が -60dB 未満なら警告)
MAXV=$(ffmpeg -hide_banner -i "$OUT" -af volumedetect -vn -f null - 2>&1 | awk '/max_volume:/{print $5}')
echo "最大音量: ${MAXV:-不明} dB" >&2
if [ -z "$MAXV" ] || awk "BEGIN{exit !($MAXV < -60)}"; then
  echo "警告: 音声がほぼ無音です。録画をやり直してください。" >&2
  [ $RC -eq 0 ] && RC=2
fi
exit $RC
