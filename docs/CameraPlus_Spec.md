# CameraPlus 総合仕様書 (Consolidated Specification)

このドキュメントは、Beat Saber MOD「CameraPlus」におけるプロファイル設定（Profile JSON）およびムーブメントスクリプト（MovementScript JSON）の全項目を網羅した包括的なリファレンスです。**ソースコード（v5.x相当）の定義に準拠しています。**

---

## 1. Profile JSON 仕様

プロファイルファイル（例: `cameraplus.json`）は、カメラの基本属性、描画設定、および初期位置を定義します。

### 全プロパティ・テーブル

| カテゴリ | プロパティ | 型 | 説明 |
| :--- | :--- | :--- | :--- |
| **基本設定** | `CameraType` | string | `ThirdPerson` または `FirstPerson` |
| | `FieldOfView` | float | 視野角（デフォルト値） |
| | `Layer` | int | 描画順序。大きいほど前面。 |
| | `AntiAliasing` | int | アンチエイリアス強度 (1, 2, 4, 8) |
| | `RenderScale` | float | 解像度スケール (0.1 〜 2.0) |
| **WindowRect**| `FitToCanvas` | bool | 画面全体にフィットさせるか |
| | `x`, `y` | int | 画面上の原点座標（左下原点） |
| | `width`, `height`| int | ピクセル単位のサイズ |
| **表示対象** | `VisibleObject` | object | 後述の詳細設定を参照 |
| **位置・回転** | `ThirdPersonPos` | object | `{x, y, z}` 三人称時の初期座標 |
| | `ThirdPersonRot` | object | `{x, y, z}` 三人称時の初期回転 |
| | `FirstPersonPos` | object | `{x, y, z}` 一人称時の位置オフセット |
| | `FirstPersonRot` | object | `{x, y, z}` 一人称時の回転オフセット |
| **拡張設定** | `CameraExtensions`| object | 後述の詳細設定を参照 |
| **エフェクト** | `CameraEffect` | object | **Profile内ではPascalCase**（後述） |

### VisibleObject (Profile)
- `Avatar`, `UI`, `ForceUI`, `Wall`, `WallFrame`, `Saber`, `CutParticles`, `Notes`: 全て **PascalCase**。
- `Debris`: `"Visible"`, `"Hidden"`, `"Link"` から選択。

### CameraExtensions（詳細設定）
- `PreviewCamera`: プレビュー窓を表示するか
- `NearClip`, `FarClip`: 描画距離
- `PositionSmooth`, `RotationSmooth`: 追従の滑らかさ
- `TurnToHead`, `TurnToHeadHorizontal`: アバター追従設定
- `DontDrawDesktop`: **trueでゲーム画面(PC)への描画を停止**

---

## 2. MovementScript JSON 仕様

スクリプトファイルは、時間の経過に伴うカメラの状態遷移を定義します。

### ルートプロパティ
- `ActiveInPauseMenu`: `true`/`false`
- `TurnToHeadUseCameraSetting`: `true`/`false`
- `Movements`: `JSONMovement` オブジェクトの配列

### Movement オブジェクトの構成要素
**重要**: スクリプト内では一部を除きプロパティ名は **PascalCase** で定義されていますが、内部キーは異なる場合があります。

- **`StartPos` / `EndPos`**: `{x, y, z, FOV}`
- **`StartRot` / `EndRot`**: `{x, y, z}`
- **`StartHeadOffset` / `EndHeadOffset`**: `{x, y, z}`
- **`Duration`**: 秒数 (float)
- **`Delay`**: 待ち時間 (float)
- **`EaseTransition`**: `true`/`false`
- **`TurnToHead`, `TurnToHeadHorizontal`**: `true`/`false`
- **`VisibleObject`**: **Script内では camelCase** (`avatar`, `ui`, `wall`, `wallFrame`, `saber`, `cutParticles`, `notes`, `debris`)
- **`CameraEffect`**: 後述（camelCase）
- **`WindowControl`**: 他カメラの制御（`Target`, `Visible`, `StartPos`, `EndPos`）

---

## 3. CameraEffect (視覚エフェクト) パラメータ

**ProfileとScriptでキー名と大文字小文字が異なるため、外部ツールでの生成時は注意が必要です。**

### 被写界深度 (DoF)
| 設定項目 | Profile JSON | MovementScript JSON |
| :--- | :--- | :--- |
| 有効化 | `EnableDOF` | `enableDoF` |
| フォーカス距離 | `DOFFocusDistance` | `dofFocusDistance` |
| フォーカス範囲 | `DOFFocusRange` | `dofFocusRange` |
| ボケ強度 | `DOFBlurRadius` | `dofBlurRadius` |
| 自動距離 | `DOFAutoDistance` | `dofAutoDistance` |

### グリッチ (Glitch)
| 設定項目 | Profile JSON | MovementScript JSON |
| :--- | :--- | :--- |
| 有効化 | `EnableGlitch` | `enableGlitchEffect` |
| ライン速度 | `GlitchLineSpeed` | `glitchLineSpeed` |
| ラインサイズ | `GlitchLineSize` | `glitchLineSize` |
| カラーギャップ | `GlitchColorGap` | `glitchColorGap` |
| フレームレート | `GlitchFrameRate` | `glitchFrameRate` |
| 頻度 | `GlitchFrequency` | `glitchFrequency` |
| スケール | `GlitchScale` | `glitchScale` |

### アウトライン (Outline)
| 設定項目 | Profile JSON | MovementScript JSON |
| :--- | :--- | :--- |
| 有効化 | `EnableOutline` | `enableOutlineEffect` |
| 強度 | `OutlineOnly` | `outlineEffectOnly` |
| 線色 | `OutlineColor` | `outlineColor`: `{r, g, b}` |
| 背景色 | `OutlineBGColor` | `outlineBackgroundColor`: `{r, g, b}` |

### ワイプ (Wipe)
- Profile: `WipeProgress`, `WipeType`, `WipeCircleCenter`
- Script: `wipeType`, `StartWipe/EndWipe` (`wipeProgress`, `wipeCircleCenter`: `{x, y}`)

---

## 4. 座標系と計算のルール

### Beat Saber 座標系 (Unity基準)
- **X**: 左右（中央0、右+）
- **Y**: 高さ（地面0、目の高さ1.5〜1.7）
- **Z**: 前後（**背後方向がマイナス**, 正面方向がプラス）

### 数学計算リファレンス
1. **水平回転 (Rot Y)**: `atan2(Cx, Cz) * 180 / PI + 180`
2. **垂直回転 (Rot X)**: `atan2(Cy - 1.3, sqrt(Cx^2 + Cz^2)) * 180 / PI`
3. **望遠距離補正**: `新しい距離 = 元の距離 * (tan(元のFOV/2) / tan(新しいFOV/2))`

---

## 5. WindowControl (オーケストレーション)

マスターカメラのMovement内に記述し、他カメラ（`Target`）を制御します。
- `x`, `y` はProfile同様、左下原点のピクセル座標。
- マスター自身を消すには `Target: "cameraplus.json", x: 5000` 等で画面外へ飛ばす。
