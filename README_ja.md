# Health × Weather AI Advisor（日本語）

本プロジェクトは、日々の健康データと天候データを組み合わせて
健康リスクを評価し、アドバイスを生成するバックエンドAPIです。

医療・ヘルスケア分野における
「環境要因 × 個人データ」の活用可能性を検証するMVPとして設計しています。

---

## 概要

- 天候データと健康データをAPI経由で取り込み
- ルールベースで健康リスクを評価
- LLMを用いて日次アドバイス文を生成
- 結果をデータベースに保存し再利用

解釈可能性と再現性を重視した設計になっています。

---

## 背景・目的

多くの健康アプリはデータの可視化に留まり、
「なぜ今日体調が悪いのか」「何に注意すべきか」
といった説明が不足していると感じていました。

本プロジェクトでは、天候などの外部要因を明示的に扱い、
人が理解しやすい形で健康リスクとアドバイスを提示することを目的としています。

---

## 開発方針

本プロジェクトでは、Gemini CLI を実装補助ツールとして利用しています。

- システム構成、API設計、データフローは開発者自身が設計
- Gemini CLI は実装の加速、ボイラープレート生成、デバッグ補助として使用

---

## 主な機能

- Open-Meteoによる天候データ取得
- 心拍数・睡眠・気分などの健康データ取り込み
- OK / Caution / Danger のリスク判定
- LLMによるアドバイス生成（フォールバックあり）
- 分析結果・アドバイスの永続化

---

## アーキテクチャ

本プロジェクトは、天候データと健康データを日付単位で統合し、
解析・文章化・保存までを一貫して行うバックエンドAPIとして設計しています。

### データフロー（概要）

1. 天候データおよび健康データを API 経由で取り込む
2. 解析モジュールにて、ルールベースで日次の健康リスクを評価
3. 評価結果（構造化JSON）をもとに、LLMが自然言語のアドバイス文を生成
4. 解析結果およびアドバイス文をデータベースに保存し、再利用する

LLMは「判断」には使用せず、
**解析結果を自然言語に変換する役割に限定**することで、
説明可能性と安全性を重視した設計としています。

APIは FastAPI により実装されており、
Webサイトや他クライアントからの利用を前提とした構成です。

---

## 使用技術（Tech Stack）

### バックエンド
- Python 3.11
- FastAPI
- SQLAlchemy
- SQLite

### AI / 解析
- Rule-based health risk evaluation
- Gemini API (LLM-based advice generation)

### 外部サービス
- Open Meteo

### インフラ / 開発ツール
- Docker / Docker Compose
- pytest

---

## 対応都市（現状）

MVPとしての検証を優先するため、
以下の都市はコード内に静的に定義しています。

- 東京
- メルボルン
- シドニー
- タスマニア

将来的には、設定ファイルやDBによる動的管理へ移行予定です。

---

## 認証

v1.0.0 よりマルチユーザー対応になりました。
データ取得・分析・アドバイス系 API はすべて JWT 認証が必要です。

### セットアップ

`.env.example` を `.env` にコピーし、`SECRET_KEY` を変更してください。

```bash
cp .env.example .env
# SECRET_KEY に openssl rand -hex 32 の出力を設定
```

### ユーザー登録

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

### ログイン（JWT 取得）

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=yourpassword"
# → {"access_token": "eyJ...", "token_type": "bearer"}
```

### 認証付きリクエスト例

```bash
TOKEN="eyJ..."   # ↑ で取得したトークン

# アドバイス取得
curl http://localhost:8000/advice/2025-12-20 \
  -H "Authorization: Bearer $TOKEN"

# 健康データ取り込み
curl -X POST http://localhost:8000/ingest/health_metrics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": {"metrics": [...]}}'

# 気象データ取り込み
curl -X POST http://localhost:8000/ingest/weather \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-12-20", "temp_max": 18.5, "temp_min": 10.2}'

# 7日間サマリー
curl http://localhost:8000/summary/last7d \
  -H "Authorization: Bearer $TOKEN"
```

### Swagger UI での動作確認

`/docs` を開き、画面右上の **Authorize** ボタンをクリックして
`username`（メールアドレス）と `password` を入力すると、
全エンドポイントを認証済み状態で試せます。

---

## API エンドポイント一覧

### 認証

| Method | Path | 説明 |
|---|---|---|
| POST | `/auth/signup` | ユーザー登録 |
| POST | `/auth/login` | ログイン・JWT 取得 |
| GET | `/auth/me` | 認証ユーザー情報取得 |

### データ（要認証）

| Method | Path | 説明 |
|---|---|---|
| POST | `/ingest/weather` | 気象データ取り込み(管理者のみ) |
| POST | `/ingest/health_metrics` | ウェアラブルデータ取り込み |
| POST | `/ingest/daily_state` | 体調ログ取り込み |
| GET | `/summary/last7d` | 直近7日間サマリー |
| GET | `/analysis/{date}` | 日次リスク分析(管理者のみ) |
| GET | `/advice/{date}` | 自然言語アドバイス生成 |

詳細なリクエスト・レスポンス仕様は、
Swagger UI（`/docs`）から確認できます。

---

## Dockerによる起動（推奨）

Dockerを使用することで、
ローカル環境にPythonをインストールせずにAPIを起動できます。

### 必要なもの
- Docker
- Docker Compose

### セットアップ

`.env` ファイルを作成し、必要な環境変数を設定してください。

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 起動方法

```
docker compose up --build
```

起動後、以下にアクセスできます： http://localhost:8000/docs

### Apple Watch + Cloudflare（任意）

Apple Watch と Cloudflare Tunnel を利用することで、
実際のウェアラブルデータを
ローカルで動作するサーバーに送信できます。

この構成は個人利用向けの拡張機能であり、
本プロジェクトの評価・動作には必須ではありません。

---

## 今後の改善予定

- 対応都市の動的管理
- Webサイトの作成
- 可読性・保守性向上のためのコードレビューおよびリファクタリング

本プロジェクトは、将来的なWebサイト化を見据えた
バックエンドAPIの設計と検証にフォーカスしています。

---

## 注意事項

本プロジェクトは学習・検証目的のものであり、
医療行為や診断を目的としたものではありません。
