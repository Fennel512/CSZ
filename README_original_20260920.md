# CSZ / FSW 图像分析与功能关联示例

从点状荧光图像出发，复现检测、对象特征提取、图像增强、FSW 扩展和蛋白功能类别关联。包含可直接运行的 Python 入口、真实和合成示例、真值坐标、CSV 表、中文说明及本机实测结果。

适用于研究和方法交流。合成示例仅每场景一幅；真实图像无人工检测真值。功能类别关联是探索性结果，不能解释为因果或独立实验验证。

## 快速开始

需要 Python 3.12。先将整个示例目录复制到自己的电脑，再在该目录打开终端。安装依赖需要联网，运行示例不需要联网、GPU、模型下载或原始 E 盘。

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_examples.py all
```

Linux/macOS（未在本次任务中实测）：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_examples.py all
```

运行结果位于 `outputs/run/`，附环境、参数、预测、图表和评价指标。重复运行会覆盖同名结果。保留多次运行时使用 `--output outputs/experiment_02`。程序只允许把运行输出写到包内 `outputs`。

## 示例与使用说明

| 任务 | 命令（前缀为上述环境中的 Python） | 说明 |
| --- | --- | --- |
| 完整性检查 | `python run_examples.py verify` | [校验与复现](docs/06_reproducibility.md) |
| 九场景识别及对象分析 | `python run_examples.py synthetic` | [CSZ 检测](docs/01_detection.md) |
| 分析自己的单通道图像 | `python run_examples.py analyze --image path/to/image.tif` | [CSZ 检测](docs/01_detection.md) |
| Fourier、小波及 BVD 扩展 | `python run_examples.py fsw` | [FSW 扩展](docs/02_fsw.md) |
| DNA/GFP 双通道分析 | `python run_examples.py real` | [真实图像特征](docs/03_real_images.md) |
| 增益、模糊、噪声与镜像 | `python run_examples.py augment` | [图像增强](docs/04_augmentation.md) |
| 蛋白功能类别关联 | `python run_examples.py function` | [功能关联](docs/05_function.md) |

## 文件和数据

- `src/`：三个未经修改的核心代码，逐文件 SHA256 可核查。
- `data/synthetic/`：九幅原始合成 TIFF 及对应真值表，原图未裁切、未改写。
- `data/real/`：五个功能类别各取一组 DNA/GFP，共十幅原始 TIFF。
- `data/function/`：313 个视野、71 个蛋白、五类的既有图像特征表；仅移除了两个本机路径字段。
- `catalog/source_manifest.csv`：本包实际包含的来源文件及 SHA256。
- `expected_results/`：本次实测指标、叠加图、参数和分组记录。
- 更广泛的 391 文件检索清单和历史 reference 源码保存在整理者的本地 Examples，未随本包分发。

[数据字典](docs/DATA_DICTIONARY.md) · [代码目录与选择依据](docs/CODE_CATALOG.md) · [实测结果](docs/VALIDATION.md) · [发布与授权说明](docs/PUBLISHING.md)

## 方法边界

CSZ-v1、FSW-BVD (mean-SWT) 和蛋白分类用的 CSZ 特征实现是三套明确区分的实现。后者不能冒充 CSZ-v1 exact-core 的同版输出。FSW 核心还含有 Enhanced-CSZ 和插值小波等历史入口，本包只验证 mean-SWT 路径。

本包采用半径约束下优先最大匹配数的一对一评价。它与历史“先最短距离分配、再按半径过滤”的匹配方式不同，因此不得直接混用两种方法的评价结果。

本次默认 CSZ 在无模糊示例上有效，但一幅图经 Gaussian sigma=1 模糊后产生大量假阳性。详见增强示例和实测报告。不要把九幅演示图的成绩当作正式测试集性能。

## GitHub

整理产物尚未上传。本发布候选包包含便携入口、数据和说明，不带虚拟环境、缓存和历史绝对路径脚本。公开前需要确认代码及示例数据的授权，见 [PUBLISHING](docs/PUBLISHING.md)。本包没有替权利人选择开源许可证。
