# 论文核心复现示例与作图数据

本包包含可离线运行的CSZ/FSW核心示例和部分论文作图表，整理日期2026-09-29。可运行入口不依赖原E盘。它覆盖方法演示和已存数值重绘；论文的全量训练、完整统计检验、AI素材和三维展示不包含在本次验证范围内。

## 快速运行

将整个文件夹复制到自己的电脑，在本目录打开终端。建议Python 3.12；安装依赖需要网络。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe verify_integrity.py
.\.venv\Scripts\python.exe run_examples.py all --output outputs/my_run
.\.venv\Scripts\python.exe run_paper_panels.py
```

核心结果保存到outputs/my_run；论文数值重绘保存到outputs/paper_replot，同名结果会覆盖。Linux/macOS可用对应Python命令，但此次未跨平台实测。此次使用已存在的科学计算环境，没有在全新环境重新安装依赖；完整实测版本见docs/environment_20260929.json。

## 包含内容

- data/synthetic：9幅合成TIFF及真值坐标；data/real：5组DNA/GFP，共10幅TIFF。
- data/function：313个视野、71个蛋白、5个功能类别的已有特征表。
- src及run_examples.py：检测、FSW、真实图像、增强和功能关联；详细方法见docs/01至06说明。
- reference_generator：原合成数据生成脚本，保留历史版本；其中绝对输出路径须改成自己的路径，不能直接当作便携入口。
- paper_data及provenance.json：Fig1、Fig3、Fig4、Fig5及S7的原始作图表和来源哈希。
- run_paper_panels.py：读取上述表，重绘五组结果图；不重新从原图测量，也不重算论文显著性。
- expected_results：原示例包基准；outputs/validation_20260929：本次重跑结果；其他既有输出属历史检查。

## 已完成的验证

六项核心入口均通过；46份CSV与历史基准在1e-10容差内一致（排除运行耗时列）。论文重绘输入哈希全部通过；Fig3c提升为4.46726479个百分点。详见docs/VALIDATION_20260929.md。

S7的5个非对照行计数与precision内部不一致，重绘图明确标记UNVERIFIED。Fig5原表的Central nuclear region与稿图VPL尚需确认。其他论文追溯问题见docs/MANUSCRIPT_ISSUES.md。

九幅合成图仅为示例，真实示例无人工检测真值。分类入口使用100棵树，不能替代历史500棵树论文训练；FSW裁剪示例与完整CSZ图像也不能直接比较性能。不同实现与匹配规则的边界见原说明README_original_20260920.md和docs。

本包没有新增代码/数据授权或上传到外部平台，授权信息见docs/PUBLISHING.md。
