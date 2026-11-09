"""路径查找辅助模块。

所有源代码和运行时数据文件（defs.txt, rules.txt）统一放在 src/ 目录下。
本模块提供各模块所需的路径常量。
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))           # src/
PROJECT_ROOT = os.path.dirname(ROOT)                         # project/

DEFS_PATH = os.path.join(ROOT, 'defs.txt')
RULES_PATH = os.path.join(ROOT, 'rules.txt')
STRUCTURE_TEMPLATES_PATH = os.path.join(ROOT, 'structure_templates.json')

NEW_PROBLEMS_DIR = os.path.join(PROJECT_ROOT, 'problems', 'problems_depth_8') # new_problems # problems_depth_6 # problems_v2
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'problems', 'depth8')
