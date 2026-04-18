# マルチカメラツール テストガイド (TESTING.md)

このプロジェクトでは、単体テストおよび統合テストに `pytest` を使用しています。

## 前提条件

- Python 3.x
- `pytest` のインストール (`pip install pytest`)

## テストの実行

### 全テストの実行
```bash
python -m pytest
```

### 詳細出力付きで実行 (Verbose)
```bash
python -m pytest -v
```

### 標準出力をキャプチャせずに実行 (printデバッグを表示)
```bash
python -m pytest -s
```

### 特定のテストファイルのみ実行
```bash
python -m pytest tests/test_integration.py
```

## テストファイルの説明

| ファイル | 説明 |
|---------|------|
| `tests/conftest.py` | Pytest フィクスチャ (サンプル SongScript, EffectScript のセットアップなど)。 |
| `tests/test_utils.py` | **単体テスト**。`multicam_utils.py` 内の数学ユーティリティ（FOV計算、距離補正、線形補間、Movement分割）を検証します。 |
| `tests/test_effects.py` | **単体テスト**。`multicam_effects.py` 内のロジック（スケジュール正規化、Visible判定）を検証します。 |
| `tests/test_effects_extra.py` | **単体テスト**。エフェクト関連の追加ケースを検証します。 |
| `tests/test_effects_outline.py` | **単体テスト**。Outline Fill / Wipe エフェクトのパラメータ生成を検証します。 |
| `tests/test_effects_symmetry.py` | **単体テスト**。Symmetric View エフェクトの位置・回転変換を検証します。 |
| `tests/test_grid_single.py` | **ジェネレータテスト**。Grid 1x1 (シングルカメラ) の `generate()` 関数を検証します。Z座標の計算結果やファイル生成を確認します。 |
| `tests/test_grid_quad.py` | **ジェネレータテスト**。Grid 2x2 の生成を検証します。4つのプロファイル/スクリプトが生成されるか確認します。 |
| `tests/test_grid_nona.py` | **ジェネレータテスト**。Grid 3x3 の生成を検証します。9つのプロファイル/スクリプトが生成されるか確認します。 |
| `tests/test_radial_chronos.py` | **単体テスト**。Radial Chronos エフェクトの遅延計算を検証します。 |
| `tests/test_scale_verify.py` | **単体テスト**。距離スケーリング計算の精度を検証します。 |
| `tests/test_schedule_debug.py` | **単体テスト**。スケジュール解決ロジックを検証します。 |
| `tests/test_slit_logic.py` | **単体テスト**。スリット計算（隣接ウィンドウ間の隙間）を検証します。 |
| `tests/test_tiling_diagnostics.py` | **単体テスト**。タイリングオフセット計算を検証します。 |
| `tests/test_integration.py` | **統合テスト**。CLI引数、ファイル生成、基本的なエフェクト動作 (`Chronos`, `Roulette`) を検証します。 |
| `tests/test_effect_combinations.py` | **網羅的エフェクトテスト**。カメラ構成 (1, 4, 9台) × エフェクト (All-Visible, Mosaic, Chronos, Roulette) の **全12パターン** を検証します。各組み合わせで正しいファイル数が生成されるか、エフェクト固有のパラメータ変化（Visible切替、遅延、FOVランダム化）が発生するかを確認します。 |
| `tests/test_validation.py` | **バリデーションテスト**。ファイル不在、壊れたJSON、BPM異常値などの異常系入力を検証します。 |

## トラブルシューティング

### エンコーディングの問題 (Windows)
PowerShell やコマンドプロンプトで `UnicodeEncodeError` が発生したり、出力が途切れる場合は、以下のコマンドで UTF-8 モードを有効にしてください。

```powershell
$env:PYTHONUTF8 = "1"
python -m pytest
```

### ジェネレータのインポートエラー
ジェネレータスクリプト (`generator_song_multicam.py`) は直接実行可能なスクリプトとして設計されています。
テストコードからは `generate` 関数をインポートして使用しますが、もしテスト実行時に `SystemExit` や引数解析エラーが発生する場合は、ジェネレータ内のメイン実行ブロックが `if __name__ == "__main__":` でガードされているか確認してください。

## テストカバレッジ (網羅性)

現在のテストスイートは、ツールの**正常動作における機能要件**をほぼ完全に網羅しています。

### カバーされている範囲 (Verified) ✅
1. **数学的正確性**: `tests/test_utils.py`
   - FOV計算、距離補正、線形補間、Movement分割などのコアロジック。
2. **ファイル生成**: `tests/test_grid_*.py`
   - シングル(1x1)、クアッド(2x2)、ノナ(3x3) のすべてのケースで、正しいファイル名とディレクトリ構造が生成されること。
   - **スリット検証**: 隣接するウィンドウ間に正確に 6px の隙間が確保されていること (WindowRect 検証済み)。
3. **エフェクトロジック**: `tests/test_effects.py` & `test_effect_combinations.py`
   - エフェクトなし、Mosaic Blink、Chronos Cascade、Dimension Roulette の全4パターンと、全グリッドサイズ(1, 4, 9台)の **計12通りの組み合わせ** 全てにおいて、期待されるパラメータ変化（Visible/Delay/FOV）が発生すること。
4. **統合動作**: `tests/test_integration.py`
   - CLI引数のパース、JSONファイルの読み込み、EffectScriptによる動的なグリッド切り替え。
5. **入力バリデーション**: `tests/test_validation.py`
   - ファイル不在、壊れたJSON、BPM異常値、Movements空配列などの異常系入力に対して、適切なエラーメッセージを出力して終了すること。

### カバーされていない範囲 (Out of Scope) ⚠️
1. **ゲーム内での視覚的評価**:
   - 生成されたJsonが「Beat Saber上で美しく見えるか」「スリット幅が適切か」といった感性的・視覚的な確認は、実機でのプレイが必要です。
2. **極端な負荷試験**:
   - 数時間の長さの譜面や、極端に細かいMovement分割（BPM 300以上など）でのパフォーマンス。
