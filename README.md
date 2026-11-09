# GeoGen

## 安装

建议 Python 3.10，运行时依赖仅为 NumPy、SciPy、Matplotlib、absl-py、tqdm。

```bash
conda create -n geogen python=3.10 -y
conda activate geogen
cd /你的路径/GeoGen
python -m pip install -r requirements.txt
```

没有 GPU 或模型 API 依赖。无显示器服务器可设置 `export MPLBACKEND=Agg`；新的二阶段发布入口已使用 Agg。

## 推荐流程：生成前提 → 一期求解 → 二期发布

### 1. 前提准备

新建一个小规模缓存示例：

```bash
python src/prgenerate.py \
  --run_mode=new \
  --target_depth=2 \
  --run_dir=problems/cache_demo \
  --output_dir=problems/premises_demo
```

默认 19 个结构模板与 13 个简单根混合生成。`target_depth` 包含末层索引，2 表示生成 depth_0、depth_1、depth_2。

缓存完成后保留；`resume` 从完成层继续，`finalize --export_depth=N` 提取指定深度。最新层不完整时，恢复逻辑会归档它并从上一完整层重做整层。

不要把尚未生成完的层通过 `--assume_complete_depth` 标为完成。层内文件配套检查不能证明所有父块都已处理；此处保留了原有层级恢复机制，没有迁移现有服务器上的任何缓存。

### 2. 一期：求解、组题并保存成功坐标

```bash
python src/fast_GeoChallenge.py \
  --input-dir problems/premises_demo \
  --output-dir outputs/run_demo \
  --workers 32
```

CPU 充足时可以增加 `--workers`；默认最多 64 个，使用单层进程池，避免再套一层 64×64 并行。每个任务处理一个前提文本文件。

一期输出 `drafts/gen_N.json`，格式为 `fast_geochallenge_draft_v2`。除原有组题信息外，新增 `GeometrySnapshot`，保存成功图形所有点的坐标和原始形式文本校验值。

重复运行默认复用已有有效草稿；更换输入、种子或美学配置做新实验时使用新的输出目录。

### 3. 二期：从快照发布

```bash
python src/complete_fast_GeoChallenge.py \
  --run-dir outputs/run_demo \
  --workers 2
```

二期默认 2 个进程，自动跳过完整已发布的 JSON+PNG；`--resume` 作为兼容参数仍可使用。中断后执行相同命令即可。

```text
outputs/run_demo/
  drafts/       # 内部草稿、证明来源、成功坐标
  published/    # 精简题目 JSON 与同名 PNG，交付时主要使用这里
  audit/        # 展示改写、翻译降级、来源证明等审计信息
  stage1_*.json
  stage2_results.jsonl
  stage2_failures.jsonl
  stage2_summary.json
```

二期不执行 DDAR，不调用 `Graph.build_problem()` 或 `Graph.copy()`，也不采样新点。它只恢复点，按题面构造已有直线/圆弧并绘图。坐标缺失或损坏会明确报错，不会偷偷回退到随机试探。

示意图仍可能因退化的选项辅助线等原因绘制失败。这时可用相同坐标仅画题设结构，并把原因写入 audit；这不是重新建图或重新挑坐标。最终是否允许这类图形降级可根据 audit 做筛选。

`recover_fast_GeoChallenge.py` 现在是同一发布器的兼容入口，不再维护另一套默认反复建图的实现。

## 保存坐标与美学优化

保存坐标不会关闭绘图中的旋转、翻转、圆弧省略、画布适配等操作。

涉及改变自由点或初始形状的美学优化，应在一期求解之前进行。可选示例：

```bash
python src/fast_GeoChallenge.py \
  --input-dir problems/premises_demo \
  --output-dir outputs/run_aesthetic \
  --workers 16 \
  --layout-trials 8
```

该开关复用 `free_params.py` 的独立图形自由参数，以及 `aestheticsEvaluator.py` 的点间排斥、角分辨率、长宽比、边界、均匀度等损失。它在原本成功的布局之外尝试指定数量的完整合法构造，选择损失更低者，然后对选中的图形进行 DDAR，最后保存其坐标。优化失败保留原成功布局。

```text
首次成功建图
→ 可选自由参数美学搜索（一期额外成本）
→ DDAR 与组题
→ 保存所选图形坐标
→ 二期从坐标绘制，并作朝向整理
```

默认 `--layout-trials=0`，即不执行美学搜索。此优化目前针对完整初始构造的布局，不是针对选项确定后的最终题面单独优化；也没有声称所有依赖点的自由度都已参数化。

不要在二期对固定坐标作独立点移动、非等比拉伸等可能改变几何关系的调整。

## 最终题目 JSON：15 个字段

| 字段                           | 含义                               |
| ------------------------------ | ---------------------------------- |
| `ID`                           | 题号，与 JSON/PNG 文件名一致       |
| `Question_zh`                  | 中文题干                           |
| `A_zh`、`B_zh`、`C_zh`、`D_zh` | 四个选项                           |
| `Answer`                       | 全部正确字母，可能多选             |
| `Prior_Difficulty`             | 原有先验分数，未改评分公式         |
| `SimplifiedFormalText`         | 规范形式化题面                     |
| `AuxiliaryFormalText`          | 参考证明对应的辅助构造；没有时为空 |
| `Auxiliary_zh`                 | 辅助构造中文描述                   |
| `ProofSteps_A`–`ProofSteps_D`  | 选项的来源证明                     |

纯净版保留 `GeoChallenge.py` 作为标准入口及核心组题函数，其最终输出也采用精简结构；性能与稳定性更推荐上述两阶段流程。标准路径仍保留原有的题面重建逻辑。

## 合并、分档和 JSONL

合并保留原来的命令形式，来源关系写入目录级 `merge_manifest.jsonl`，并在 audit 中保留支持中断恢复的映射。

```bash
python src/merge_published_datasets.py \
  --input-dir outputs/run_demo \
  --input-dir outputs/run_other \
  --output-dir datasets/merged
```

分档与参考抽样默认使用 70/90 标准，每档参考 100 题，也可手动覆盖阈值：

```bash
python src/prepare_difficulty_dataset.py \
  --input-dir datasets/merged \
  --reference-dir datasets/reference_70_90 \
  --output-dir datasets/Geo \
  --easy-upper 70 --medium-upper 90 --reference-count 100
```

参考样本仍属于完整数据集，不是独立留出的训练/测试划分。

```bash
python src/export_problem_jsonl.py outputs/run_demo/published
```

按阈值筛题可运行 `src/filter_problems_by_difficulty.py`

