# 提出概要（日本語）

## 作品名

車なし生活リハーサル / Carless Life Rehearsal

## 社会課題

高齢者が運転免許を自主返納するとき、本人と家族は「返納後も日常生活が成り立つのか」という移動不安を抱えます。

この不安は、単に最短経路があるかどうかでは解消できません。重要なのは、本人の歩行時間、乗り換え回数、待ち時間、帰りの便、階段回避などを踏まえて、スーパー、病院、薬局、市役所、駅、交流の場に現実的に行けるかです。

## コアアイデア

免許返納前に、車なし生活を小さくリハーサルします。返納後も同じアプリを、音声中心の日常外出アシスタントとして使えます。

アプリは返納を勧めたり、返納可否を決定したりしません。提供するのは、移動可能性の情報と確認材料です。

## 公共交通オープンデータの利用

想定するデータは以下です。

- GTFS / ODPT
- 停留所、駅、路線、時刻表
- 運行日カレンダー
- 乗り換え、待ち時間、徒歩時間
- 任意のデマンド交通情報
- MobilityData GTFS Validator JSON または軽量内部チェックによるデータ品質警告

第一段階のデモは、外部APIキーなしで動くfixtureデータとmock routerを使います。第二段階でOpenTripPlanner GraphQL adapterを通じてGTFS/ODPT由来の経路に接続します。

## UI/UX

- 老人端は大きなボタン、短い日本語、音声読み上げ中心です。
- 地図は老人端の主画面ではありません。
- 家族/自治体向けにMapLibreの地図とレポートを用意します。
- 音声入力が使えないブラウザでも、大きなボタンで同じ操作ができます。

## 技術実装

- Backend: FastAPI, Python 3.12互換, Pydantic, pytest
- Frontend: Vite, React, TypeScript
- Routing: MockRoutingProvider, OTPRoutingProvider
- Map: MapLibre GL JS
- Voice: Web Speech API speechSynthesis, react-speech-recognition
- Data Quality: GTFS Validator JSON取り込み口、内部軽量チェック、`/data-quality`

## 制限

- 医療、介護、法律の助言ではありません。
- 安全を保証するナビゲーションアプリではありません。
- 免許返納の判断を代行しません。
- データ不足は「判定不能」または警告として表示します。
- 生のODPT/チャレンジデータは再配布しません。

## 公開性

コンテスト期間中、外部APIキーなしで動作するfixture demoを無料で公開できます。実データ接続は環境変数で任意に設定する設計です。
