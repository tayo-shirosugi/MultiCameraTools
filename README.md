# マルチカメラツール (Multi-Camera Tools)

WebAssembly版:
https://tayo-shirosugi.github.io/MultiCameraTools/

Beat Saber の CameraPlus 向けに、複数カメラの MovementScript を自動生成するツールセットです。
楽曲の進行に合わせてカメラ台数を動的に切り替え（1→4→9→16台）、各カメラを個別スクリプトで制御することができます。

## 概要

このツールは既存の CameraPlus MovementScript（`SongScript.json`）と、演出を定義する `EffectScript.json` を入力として受け取り、3×3 や 2×2 の**回転タイリング方式**でマルチカメラ構成に変換します。
指定した時間スケジュールに応じて、カメラの台数を動的に切り替えたり、様々な視覚エフェクトを適用することができます。

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
| `-n`, `--name` | プロファイル(フォルダ)名およびスクリプトファイル名のプレフィックス | 任意 |

### EffectScript.json の書き方

カメラの切り替えタイミングや適用するエフェクトをJSONファイルで指定します。
エフェクト固有のパラメータは、各スロット内の同階層に記載します。

```json
{
  "bpm": 170,
  "schedule": [
    {
      "start": 0,
      "end": 30,
      "cameras": 9,
      "effect": "mosaic-blink"
    },
    {
      "start": 30,
      "end": 60,
      "cameras": 4,
      "effect": "symmetry-view",
      "symmetry_type": "mirror",
      "outline_side": "right",
      "color_line": {"r": 1.0, "g": 0.0, "b": 1.0},
      "color_bg": {"r": 0.1, "g": 0.1, "b": 0.1}
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `bpm` | float | 楽曲のテンポ |
| `schedule[].start` | float | 開始秒 |
| `schedule[].end` | float/null | 終了秒。null=曲末尾まで |
| `schedule[].cameras` | int | カメラ台数 (1/4/9/16) |
| `schedule[].effect` | string | エフェクト名。省略時または未定義時は `"all-visible"` |
| `schedule[].*` | - | 各エフェクト固有のパラメータ |

※サンプル全体については `examples/sample_effect_script.json` を参照してください。

### 利用可能なエフェクト一覧

| エフェクト名 (`effect`) | 概要 | 主要なパラメータ |
|-----------------------|------|-----------------|
| `all-visible` | 全カメラを常時表示（デフォルト） | なし |
| `clone-grid` | 全カメラが同一の正面映像を映す（タイリングオフセット=0） | なし |
| `mosaic-blink` | グリッドが市松模様で映像/黒を交互に切替 | なし |
| `mosaic-shuffle` | ランダムなカメラパネルが確率で表示/非表示 | `density`: 生存確率 (0.0-1.0) |
| `chronos-cascade` | 列ごとに過去映像を遅延再生（右列=リアル、左列=-1秒等） | `delay`: 列ごとの遅延秒数 |
| `radial-chronos` | 中央から外側に向かって動きが波紋のように伝播 | `delay`: 単位距離あたりの遅延秒数 |
| `diagonal-wave` | 左上から右下に向かって動きが伝播 | `delay`: ステップごとの遅延秒数 |
| `dimension-roulette` | FOVとRollがランダム変化。Deterministic Random で再現性あり | なし |
| `vortex-spin` | 各カメラを渦巻状に回転（Z軸）させる | `speed`: 回転速度, `mode`: "sync"/"wave" |
| `split-view` | 左列/中央列/右列が別アングルからアバターを捉える | `angle`: 左右の回り込み角度 (デフォルト 90) |
| `surround-view` | 4台で正面/右/背後/左からアバターを囲む | — (2×2のみ) |
| `panoptic-view` | 中央1台+周囲8台で360度囲む | — (3×3のみ) |
| `symmetry-view` | 右半分が左半分の鏡像（または点対称）になる | `symmetry_type`: "mirror"/"point", `outline_side` |
| `outline-fill` | 左上から順にアウトラインで塗りつぶし | `step_delay`: 遅延ビート, `color_line`, `color_bg` |
| `outline-wipe` | 左上から順にアウトラインが通過して戻る | `step_delay`: 遅延ビート, `color_line`, `color_bg` |
| `random-outline-fill`| ランダムな順序でカメラを実像で満たす | `duration_beats`: 全体の所要ビート, `color_line`, `color_bg` |

---

## デプロイ方法

```bash
python generator_song_multicam.py -i SongScript.json -e EffectScript.json -o output_dir -n MySong
```

生成後、以下の手順で Beat Saber に配置します。

1. `output_dir/Profiles/[プロファイル名]/` → `UserData/CameraPlus/Profiles/[プロファイル名]/`
2. `output_dir/Scripts/` → `UserData/CameraPlus/Scripts/`
3. ゲーム起動後、CameraPlus のプロファイル選択で `[プロファイル名]` を選択

> **💡 ヒント**: アップデート時は、前のファイルを削除する手間を省き不要な干渉を防ぐため、**出力時に新しいプレフィックスを指定（例：`MySong_v2`）し、別プロファイルとして追加**することをおすすめします。同じ名前のプロファイルに上書き配置すると、古いカメラファイルが残ってしまい表示が崩れる原因になります。

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

## 既知の制約

- **オイラー角の限界**: カメラが大きく傾いた構図ではタイリングがズレる（将来的にクォータニオンベース化が必要）
- **TurnToHead との非互換**: `TurnToHead` / `TurnToHeadHorizontal` は水平タイリングと干渉するため、グリッドカメラから自動除外される
- **WindowControl のサイズ変更不可**: ウィンドウサイズはプロファイルで静的に設定する必要がある
- **歪みの発生**: 回転タイリングは視差ズレを解消できますが、平面投影の原理上、つなぎ目で直線がわずかに「くの字」に折れる場合があります。

---

## ライセンス

MIT License
