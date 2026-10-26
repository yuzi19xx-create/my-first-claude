import html
D=[
("開会・ご案内",0,[
 ("ユーザーグループのルール",21,["自己宣伝・売り込みは禁止","同意なしにグループ外で連絡しない","共有された事例は他へ持ち出さない"]),
 ("録画のお知らせ",75,["YouTubeチャンネルで公開される"]),
 ("Bevy / Champion Office Hours",106,["Bevyに登録してMUGとつながる"]),
 ("Adobe Championプログラム",144,["応募受付中・40名のChampion","紹介セッションあり(205)"]),
 ("イベント案内",230,["Adobe AI Forum(マドリード・ボストン・コロンバス)","北米の今後のユーザーグループ(263)"]),
]),
("アジェンダ・登壇者",323,[
 ("本日のアジェンダ",323,["AI機能 → 構造 → 命名規則 → フォルダ/ガバナンス → キャンペーン種類 → COE → トークン → チャネル"]),
 ("登壇者",344,["Karina Vidal(Bonterra)","Beth Corby(Shift Paradigm)","Chris Kelley"]),
]),
("Marketo × AI の連携",457,[
 ("AI連携の方法",457,["Marketoがリードデータ・プロンプト・文脈・履歴を送る","大量データのAI拡充などに活用"]),
 ("AIは自動化だけではない",569,["API・Webhook・iPaaS・MCPで外部LLMをワークフローにつなぐ"]),
 ("新しい運用能力",688,["コンテンツ生成","ダイナミックなパーソナライズ","リードスコアリングの強化","予測セグメンテーション"]),
 ("GenAIの同意",776,["同意への署名を忘れずに"]),
]),
("AIには構造が必要",825,[
 ("AIの賢さはインスタンスの構造しだい",825,["トークンの不統一","命名規則の乱れ","ライフサイクル段階が不明確","テンプレートがない"]),
 ("AIはビジネスを自動では理解しない",891,[]),
 ("構造がなければAIは混乱を加速する",918,["強い運用の土台が前提"]),
]),
("命名規則",1009,[
 ("AI時代に命名規則が重要な理由",1009,["AIがアセットを分類","自動化が意図を推測","関連プログラムの提案"]),
 ("命名規則は「AIのメタデータ」",1097,["プログラム名は80文字以内","ブランド.YYYY.MM.チャネル.ソース.キャンペーン名.タイプ"]),
 ("AI対応の命名戦略",1289,["What / Who / Where / When を名前に含める"]),
 ("AIが命名を気にする理由",1350,["分類・検索・推薦・パターン認識"]),
 ("予測できる組織の文脈",1423,[]),
]),
("フォルダ構造とガバナンス",1449,[
 ("フォルダ構造が重要な理由",1449,["予測できる組織パターン","アセットを見つけやすく","重複プログラムを減らす"]),
 ("運用のガードレール",1555,["ガバナンス:運用ルールの定義","権限:誰が何をできるか"]),
]),
("キャンペーンの種類",1685,[
 ("キャンペーンの分類",1685,["Operational:データ衛生・同期・スコアリング","Executable:再利用できる一元化ワークフロー"]),
 ("Executable と Request の違い",1767,["Executable:中核の処理ロジック","Request:実行依頼の入口"]),
 ("AIが呼び出せるインフラに",1893,["MCP・iPaaS・LLMがツールを見つけて実行できる"]),
]),
("Center of Excellence(COE)",1975,[
 ("COEの役割",1975,[]),
 ("COEとは",2006,["標準・フレームワーク・運用の一貫性を確立"]),
 ("COEがAI対応を支える",2042,["再現できる構造","ガバナンス","不整合の削減","予測できる自動化"]),
]),
("トークン戦略",2134,[
 ("トークンは構造化されたAIコンテキスト",2134,["再利用しやすく・ローカライズしやすく・AIが構造を推論"]),
 ("コアとなるトークン階層",2243,["マイトークン(プログラム)","パーソン(個人)トークン"]),
 ("トークン + MCP + AIエージェント",2303,["エージェントがスキーマを読んで値を入力"]),
 ("AI運用エージェントのデモ",2400,[]),
 ("エージェント化されたオペレーション",2465,["テンプレート選択 → 値入力 → ローカライズ → 実行依頼"]),
]),
("チャネルとライフサイクル",2516,[
 ("運用ステージと文脈",2516,[]),
 ("チャネル設定が重要な理由",2548,["ステータスがエンゲージメントのシグナルになる"]),
 ("ライフサイクルが重要な理由",2608,["匿名 → 既知 → エンゲージ → MQL → SAL → SQL → 商談"]),
 ("チャネル + ライフサイクル",2649,["行動(チャネル)と進み具合(ライフサイクル)で文脈をつくる"]),
]),
("Marketo AIの行き先",2693,[
 ("AI支援のオペレーションへ",2693,[]),
 ("Marketo AIが向かう先",2714,["手動・静的 → AI支援のワークフロー"]),
 ("ロードマップのハイライト",2795,["会話型AIワークスペース","スマートキャンペーンにAI組み込み"]),
 ("外部AIから標準搭載AIへ",2929,[]),
]),
("AIの活用領域",2939,[
 ("運用効率化のためのAI",2939,["最も早くROIを得やすい","キャンペーン監査・ガバナンス検出・リスク特定・最適化提案"]),
 ("画像・コンテンツ生成",3091,["画像・件名・LPコピー・ナーチャリング・ローカライズ・CTA"]),
 ("意思決定と最適化",3150,["ファネル速度・エンゲージメント・コンバージョン・アトリビューションを分析"]),
]),
("まとめ",3249,[
 ("AI導入には新しいツール以上のものが必要",3249,["戦略・構造・運用の準備"]),
 ("AI対応チェックリスト",3260,["ユースケースと目標を定義","命名規則・プロセス・チャネル設定の標準化","フォルダ構造・権限・ガバナンス"]),
 ("質疑応答",3357,[]),
]),
]
def f(s): s=int(s); return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}" if s>=3600 else f"{s//60}:{s%60:02d}"
def lk(t,txt,c=''): return f'<a class="{c}" href="index.html#t={t}" target="main">{html.escape(txt)}</a>'
body=''
for i,(ch,t,leaves) in enumerate(D,1):
    body+=f'<li class="ch c{i%6}"><details open><summary>{lk(t,f"{i}. {ch}","h")}<span class="tm">{f(t)}</span></summary><ul>'
    for lt,ls,pts in leaves:
        body+=f'<li class="lf"><div>{lk(ls,lt)}<span class="tm">{f(ls)}</span></div>'
        if pts: body+='<ul class="pt">'+''.join(f'<li>{html.escape(p)}</li>' for p in pts)+'</ul>'
        body+='</li>'
    body+='</ul></details></li>'
page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>マインドマップ — Marketo Fundamentals for AI</title>
<style>
:root{{--bg:#f4f4f6;--fg:#222;--card:#fff;--ln:#bbb;--tm:#888}}@media(prefers-color-scheme:dark){{:root{{--bg:#17171c;--fg:#e8e8ee;--card:#23232b;--ln:#555;--tm:#999}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Hiragino Sans",sans-serif;line-height:1.5}}
header{{background:#1a1a2e;color:#fff;padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}header h1{{font-size:18px;margin:0;flex:1}}
button,header a{{font-size:13px;padding:6px 10px;cursor:pointer;color:#000;background:#eee;border:1px solid #888;border-radius:4px;text-decoration:none}}
main{{padding:20px;overflow-x:auto}}.root{{display:inline-block;background:#e0457b;color:#fff;font-weight:bold;padding:12px 18px;border-radius:24px;margin-bottom:12px}}
ul{{list-style:none;margin:0;padding:0 0 0 22px}}main>ul{{padding-left:0}}li{{position:relative}}
.ch{{margin:10px 0}}.ch>details>summary{{cursor:pointer;display:inline-flex;gap:8px;align-items:baseline;padding:6px 12px;border-radius:8px;background:var(--c);color:#fff}}
.ch>details>summary a{{color:#fff;font-weight:bold;text-decoration:none}}.ch>details>summary .tm{{color:#fffc}}
.ch>details>ul{{border-left:3px solid var(--c);margin-left:14px;padding-top:6px}}
.c1{{--c:#2f7de1}}.c2{{--c:#1a9e75}}.c3{{--c:#d9822b}}.c4{{--c:#8a5cd6}}.c5{{--c:#c9484f}}.c0{{--c:#2a8f9e}}
.lf{{margin:6px 0;padding-left:8px}}.lf>div a{{color:var(--fg);font-weight:600;text-decoration:none;border-bottom:1px dotted var(--ln)}}.lf>div a:hover{{color:var(--c)}}
.tm{{font-size:11px;color:var(--tm);margin-left:6px}}.pt{{font-size:13px;color:var(--fg);opacity:.85}}.pt li{{padding-left:14px}}.pt li:before{{content:"・";position:absolute;left:0}}
</style></head><body><header><h1>マインドマップ — Marketo Fundamentals for AI</h1><button id="o">すべて開く</button><button id="c">すべて閉じる</button><a href="index.html" target="main">日本語スライド資料へ</a></header>
<main><div class="root">Marketo Fundamentals for AI</div><ul>{body}</ul></main>
<script>const dd=()=>document.querySelectorAll('details');o.onclick=()=>dd().forEach(d=>d.open=true);c.onclick=()=>dd().forEach(d=>d.open=false);
document.querySelectorAll('summary a').forEach(a=>a.addEventListener('click',e=>e.stopPropagation()));</script></body></html>'''
open('out/mindmap.html','w').write(page)
