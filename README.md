# マルチカメラツール (Multi-Camera Tools)

Beat Saber の CameraPlus 向けに、複数カメラの MovementScript を自動生成するツールセットです。
楽曲の進行に合わせてカメラ台数を動的に切り替え（1→4→9→16台）、各カメラを個別スクリプトで制御することができます。

## 概要

このツールは既存の CameraPlus MovementScript（SongScript）を入力として受け取り、
3×3 や 2×2 の**回転タイリング方式**でマルチカメラ構成に変換します。
BPM 同期エフェクトや動的グリッド切替にも対応しています。

詳細な使い方は下記の「使い方」セクションを参照してください。

---

## ファイル構成

```
MultiCameraTools/
├── generator_song_multicam.py   # メインジェネレータ (CLI)
├── multicam_utils.py            # 数学ユーティリティ (FOV計算、距離補正、線形補間)
├── multicam_effects.py          # EffectScript読込、スケジュール検索、エフェクト生成
├── examples/                    # サンプル EffectScript
├── docs/                        # 仕様ドキュメント
└── tests/                       # 単体テスト・統合テスト
```

### モジュール構成

| ファイル | 役割 |
|---------|------|
| `generator_song_multicam.py` | CLI + 生成メイン処理 |
| `multicam_utils.py` | 数学ユーティリティ（FOV計算、距離補正、線形補間、Movement分割） |
| `multicam_effects.py` | EffectScript読込、スケジュール検索、Visible判定 |
| `tests/test_utils.py` | multicam_utils の単体テスト |
| `tests/test_effects.py` | multicam_effects の単体テスト |

---

## インストール

Python 3.8 以上が必要です。追加ライブラリは不要です。

```bash
git clone https://github.com/tayo-shirosugi/MultiCameraTools.git
cd MultiCameraTools
```

---

## 使い方

### 基本

```bash
# 基本的な実行方法
python generator_song_multicam.py -i SongScript.json -e EffectScript.json

# 出力先と名前を指定する場合
python generator_song_multicam.py -i SongScript.json -e EffectScript.json -o output_dir -n MyProject
```

| 引数 | 説明 | 必須 |
|------|------|------|
| `-i`, `--input` | 元となる `SongScript.json` のパス | **必須** |
| `-e`, `--effect-script` | `EffectScript.json` のパス | **必須** |
| `-o`, `--output` | 生成物の出力先ディレクトリ | 任意 |
| `-n`, `--name` | プロファイル名のプレフィックス | 任意 |

### EffectScript JSON フォーマット

```json
{
  "bpm": 170,
  "schedule": [
    {"start": 0,   "end": 30,   "cameras": 9, "effect": "mosaic-blink"},
    {"start": 30,  "end": 60,   "cameras": 1},
    {"start": 60,  "end": null,  "cameras": 9, "effect": "all-visible"}
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `bpm` | float | テンポ。Movementをビート単位に分割 |
| `beats_per_sub` | int | 1つのMovementを何ビートごとに分割するか (デフォルト 1) |
| `schedule[].start` | float | 開始秒 |
| `schedule[].end` | float/null | 終了秒。null=曲末尾まで |
| `schedule[].cameras` | int | カメラ台数 (1/4/9/16) |
| `schedule[].effect` | string | エフェクト名。省略時または未定義時は `"all-visible"` |
| `schedule[].*` | - | 各エフェクト固有のパラメータ（後述） |

### 利用可能なエフェクト一覧

| エフェクト名 (`effect`) | 概要 | 主要なパラメータ |
|-----------------------|------|-----------------|
| `all-visible` | 全カメラを常時表示（デフォルト） | なし |
| `mosaic-blink` | カメラを市松模様状に交互に点滅表示 | なし |
| `mosaic-shuffle` | 指定した密度でランダムにカメラを点滅 | `density`: 生存確率 (0.0-1.0) |
| `chronos-cascade` | 列ごとに時間を遅延させ、波のような効果 | `delay`: 列ごとの遅延秒数 |
| `radial-chronos` | 中心からの距離に応じて時間を遅延 | `delay`: 単位距離あたりの遅延秒数 |
| `diagonal-wave` | 左上から斜め方向に時間を遅延 | `delay`: ステップごとの遅延秒数 |
| `dimension-roulette` | FOVとZ回転（Roll）をランダムに変動 | なし |
| `vortex-spin` | 各カメラを渦巻状に回転（Z軸）させる | `speed`: 回転速度, `mode`: "sync"/"wave" |
| `split-view` | 3列構成時、左右を外側に向ける (三面鏡風) | `angle`: 外側への回転角度 (デフォルト 90) |
| `surround-view` | 4台構成時、前後左右の4方向を向ける | なし |
| `panoptic-view` | 9台構成時、中央1台+周囲8方向を囲む | なし |
| `symmetry-view` | 対称配置を行い、アウトラインで強調 | `symmetry_type`: "mirror"/"point", `outline_side`: "left"/"right" |
| `outline-fill` | 輪郭線のみの状態から徐々に実像で満たす | `step_delay`: 遅延ビート, `color_line`, `color_bg` |
| `outline-wipe` | 輪郭線で画面を塗りつぶし、実像を消す | `step_delay`: 遅延ビート, `color_line`, `color_bg` |
| `random-outline-fill`| ランダムな順序でカメラを実像で満たす | `duration_beats`: 全体の所要ビート, `color_line`, `color_bg` |

### エフェクトパラメータの指定例

```json
{
  "start": 10,
  "cameras": 4,
  "effect": "symmetry-view",
  "symmetry_type": "mirror",
  "outline_side": "right",
  "color_line": {"r": 1.0, "g": 0.0, "b": 1.0},
  "color_bg": {"r": 0.1, "g": 0.1, "b": 0.1}
}
```

サンプル設定の詳細は `examples/sample_effect_script.json` を参照してください。

---

## デプロイ方法

```bash
python generator_song_multicam.py -i SongScript.json -e EffectScript.json -o output_dir -n MySong
```

生成後、以下の手順で Beat Saber に配置します。

1. `output_dir/Profiles/SongMultiCam/` → `UserData/CameraPlus/Profiles/SongMultiCam/`
2. `output_dir/Scripts/` → `UserData/CameraPlus/Scripts/`
3. ゲーム起動後、CameraPlus のプロファイル選択で `SongMultiCam` を選択

> **⚠️ 注意**: アップデート時は `UserData/CameraPlus/Profiles/SongMultiCam` フォルダを**必ず一度全削除**してからファイルを配置してください。古いプロファイルが残っていると意図しないカメラが表示されます。

---

## テスト

```bash
python -m pytest tests/ -v
```

テストの詳細については [`docs/TESTING.md`](docs/TESTING.md) を参照してください。

---

## 動作原理

1. 元スクリプトのFOVを無視し、全カメラのFOVを固定10°に強制（歪み防止）
2. 元FOV / grid_size（タイル1枚分のFOV）→ 10° への距離補正で見かけの大きさを維持
3. 回転タイリングオフセットを適用（全カメラを同一座標に配置し、角度のみ変える）
4. マスターカメラ(cameraplus)は独立オーケストレーター。自身をWindowControlで画面外（x=5000）に退避
5. グリッドカメラ（Cam_Grid3_01〜09 等）は個別にタイリングオフセット付きスクリプトを持つ

---

## 実装済みエフェクト

共通前提: Mosaic Blink / Chronos Cascade / Dimension Roulette には BPM 同期の **Movement 分割**が必要です（BPM指定で既存Movementを細分化し、線形補間でキーフレームを生成）。

| # | エフェクト名 | 概要 | 主なパラメータ |
|---|------------|------|---------------|
| 1 | **Mosaic Blink** | グリッドが市松模様で映像/黒を交互に切替 | — |
| 2 | **Chronos Cascade** | 列ごとに過去映像を遅延再生（右列=リアル、左列=-1秒等） | `delay` (秒/列) |
| 3 | **Radial Chronos** | 中央から外側に向かって動きが波紋のように伝播 | `delay` (秒/距離) |
| 4 | **Dimension Roulette** | FOVとRollがランダム変化。Deterministic Random で再現性あり | — |
| 5 | **Clone Grid** | 全カメラが同一の正面映像を映す（タイリングオフセット=0） | — |
| 6 | **Outline Fill** | 左上から順にアウトラインで塗りつぶし | `step_delay`, `color_line`, `color_bg` |
| 7 | **Outline Wipe** | 左上から順にアウトラインが通過して戻る | `step_delay`, `color_line`, `color_bg` |
| 8 | **Vortex Spin** | 全カメラがZ軸回転 | `speed` (deg/sec), `mode` ("wave"で遅延伝播) |
| 9 | **Symmetric View** | 右半分が左半分の鏡像（または点対称）になる | `symmetry_type` ("point"/"mirror"), `outline_side` |
| 10 | **Diagonal Wave** | 左上から右下に向かって動きが伝播 | `delay` |
| 11 | **Mosaic Shuffle** | ランダムなカメラパネルが確率で表示/非表示 | `density` (0.0〜1.0) |
| 12 | **Split View** | 左列/中央列/右列が別アングルからアバターを捉える | `angle` (左右の回り込み角度) |
| 13 | **Surround View** | 4台で正面/右/背後/左からアバターを囲む | — (2×2のみ) |
| 14 | **Panoptic View** | 中央1台+周囲8台で360度囲む | — (3×3のみ) |

---

## CameraPlus 利用上の注意

### プロファイルのキャッシュ

CameraPlus のプロファイルはキャッシュ機能があります。起動後に同名プロファイルの内容を変更しても反映されない場合があります。新しいプロファイルを使用する際は、以下の手順を推奨します。

1. Beat Saber を起動する
2. マップ選択前に、**すでに動作確認済みの**プロファイルを GAME にセットする
3. マップ開始後に、**新たに作成した**プロファイルを Load する
4. マップを終了する
5. 新しいプロファイルを GAME にセットし直す
6. マップを開始する

### WindowControl の制約

- `WindowControl` ではウィンドウ**サイズ変更は不可**。サイズはプロファイル（`.json`）に静的に設定すること
- マスターカメラは必ず `WindowControl` で**自身を画面外（x=5000）に退避**させること。`FitToCanvas: true` のカメラは Layer に関わらず前面に出る場合がある

### プロファイルの最小構成（実機確認済み、~700B）

```json
{
  "CameraType": "ThirdPerson",
  "FieldOfView": 10.0,
  "VisibleObject": { "avatar": true, "ui": false, "wall": true, "saber": true, "notes": true, "debris": "Link" },
  "Layer": -68,
  "AntiAliasing": 2,
  "RenderScale": 1.0,
  "WindowRect": { "FitToCanvas": false, "x": 5000, "y": 724, "width": 636, "height": 356 },
  "MovementScript": { "MovementScript": "ScriptName.json", "UseAudioSync": true },
  "CameraExtensions": { "dontDrawDesktop": false },
  "ThirdPersonPos": { "x": 0, "y": 1.0, "z": 0 },
  "ThirdPersonRot": { "x": 0, "y": 0, "z": 0 }
}
```

> `FirstPersonPos`, `CameraLock`, `Multiplayer`, `VMCProtocol`, `WebCamera`, `CameraEffect` 等は省略可能です。

### WindowRect の座標系

- **左下原点**: `(x=0, y=0)` が画面左下、`y` を大きくすると上方向
- ファイル読み込み: `UserData/CameraPlus/Profiles/` 配下のフォルダ内の**全 `.json` ファイル**がカメラとして読み込まれる

---

## 既知の制約

- **オイラー角の限界**: カメラが大きく傾いた構図ではタイリングがズレる（将来的にクォータニオンベース化が必要）
- **TurnToHead との非互換**: `TurnToHead` / `TurnToHeadHorizontal` は水平タイリングと干渉するため、グリッドカメラから自動除外される
- **WindowControl のサイズ変更不可**: ウィンドウサイズはプロファイルで静的に設定する必要がある
- **歪みの発生**: 回転タイリングは視差ズレを解消するが、平面投影の原理上、つなぎ目で直線が「くの字」に折れる場合がある（FOVを絞ること＝10°以下で大幅に軽減可能）

---

## ライセンス

MIT License
