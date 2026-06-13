# Database Design Reference

このファイルはデータベースの詳細設計資料です。
README に掲載する概要説明ではなく、各テーブルの役割・設計意図・将来的な拡張方針をまとめています。

---

## Table Summary

| テーブル名 | データの種類 | 主なカラム | 単位 | user_id | 役割 | なぜ必要か |
|---|---|---|---|---|---|---|
| `users` | 認証・ユーザー管理 | id, email, hashed_password, is_active, is_admin | — | なし（親） | ユーザー認証とアカウント管理 | マルチユーザー対応と、全個人データの分離起点となる親テーブル |
| `weather` | 共通参照データ | id, date, temp_max, temp_min, precipitation_sum | °C, mm | **なし（意図的）** | 地域の気象参照データ | 気象は地域に紐づく共通情報のため、ユーザー分離は不要。全ユーザーが同一の気象データを参照する |
| `health_metrics` | 日次集計 | id, user_id, date, steps, sleep_hours, resting_hr | 歩, 時間, bpm | あり | 旧来の日次集計テーブル | 旧アーキテクチャとのスキーマ継続性のために保持。将来的には時系列テーブルに統合予定 |
| `daily_state` | 日次記録（主観） | id, user_id, date, mood, symptoms, notes | 1〜5, 症状コード | あり | 気分・症状・メモの日次ログ | 客観データ（心拍・歩数）と主観データ（気分・症状）を組み合わせることで、リスク評価の精度を高める |
| `health_metric_raw` | 生データ保存 | id, user_id, received_at, payload_json | JSON | あり | Apple Health エクスポートの生ペイロード保存 | パースロジックが変わっても元データから再処理できる。受信した全データの監査証跡にもなる |
| `sleep_sessions` | 時系列データ | id, user_id, session_start/end_time, total_sleep_hours, deep/rem/core_hours | 時間, timestamptz | あり | 睡眠セッション記録 | 睡眠時間・深さはリスク評価の主要指標。セッション単位で保存することで日をまたぐ睡眠を正確に扱える |
| `resting_heart_rates` | 時系列データ | id, user_id, timestamp, value | bpm, timestamptz | あり | 安静時心拍数の時系列記録 | 7日間平均からの乖離を「疲労・体調変化」の指標として使用。日次分析で参照される |
| `step_counts` | 時系列データ | id, user_id, timestamp, value | 歩, timestamptz | あり | 歩数の時系列記録 | 活動量の偏差を「高負荷」指標として使用。睡眠不足と組み合わせて疲労リスクを判定する |
| `indicator_thresholds` | 分析設定 | user_id(PK), indicator_name(PK), caution_threshold, danger_threshold, false_alarm_count, event_at_ok_count | °C / mm / σ / 時間 / bpm（指標による） | あり（複合PK） | ユーザーごとのアラート閾値管理 | 感度は個人差が大きい。誤検知・見逃しの履歴に基づき、ルールベースで閾値を調整できる設計 |
| `daily_advice` | キャッシュ（生成済み） | id, user_id, date, overall_level, total_points, advice_text, source | — | あり（UNIQUE user_id+date） | AI生成アドバイスのキャッシュ | 同一ユーザー・同日のアドバイスを1回だけ生成してキャッシュし、LLM APIの呼び出しコストと遅延を削減する |

---

## Design Decisions

### User-scoped data isolation

Personal health data tables carry a `user_id` foreign key referencing `users.id`.
CRUD queries are scoped by `user_id` to support user-level data separation.

`users` テーブルを除く全ての個人健康データテーブルに `user_id` FK を持たせることで、
クエリ層でのユーザー境界を明確にしています。

### Weather as shared reference data

`weather` テーブルは意図的に `user_id` を持ちません。
気象は地域に紐づく環境参照データであり、ユーザーごとに分ける必要がないためです。
全ユーザーが同一日付の気象レコードを共有します。

ER図上でリレーションを持たないのはバグではなく設計上の判断です。

### health_metrics の位置づけ

`health_metrics` は旧アーキテクチャ時代の日次集計テーブルです。
現在は `sleep_sessions`・`resting_heart_rates`・`step_counts` の時系列テーブルが主役であり、
`health_metrics` はスキーマ継続性のために保持しています。

将来的には時系列テーブルへの統合を検討しています。

### Per-user thresholds with rule-based adjustment

`indicator_thresholds` は複合主キー `(user_id, indicator_name)` を使用します。
8種類の健康指標（高気温・低気温・降水量・気温差・活動量・睡眠不足・安静時心拍数・疲労蓄積）の
閾値をユーザーごとに独立して管理します。

閾値は誤検知（false alarm）と見逃し（event at OK）の履歴カウントに基づき、
ルールベースで Caution / Danger ラインを上下に調整できる設計です。
感度の個人差に対応するため、固定閾値ではなくユーザーごとの動的な設定を採用しています。

### Advice caching

`daily_advice` に `UNIQUE(user_id, date)` 制約を設けています。
同一ユーザー・同一日付のアドバイスは1回だけ生成され、以降のリクエストはキャッシュから返します。

LLM API（Gemini）の呼び出しコストとレイテンシを削減するための設計です。
`source` カラムにより、LLM 生成かフォールバックかを区別できます。

### Raw data preservation

`health_metric_raw` は Apple Health Auto Export のペイロードをパース前の状態で JSON として保存します。

パースロジックを変更した場合でも、保存済みの生データから過去分を再処理できます。
また、受信した全データの監査証跡としても機能します。
