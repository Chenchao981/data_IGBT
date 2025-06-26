#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FT数据清洗工具 - 安全打包脚本 (PYZ格式)
功能：创建不包含敏感信息的压缩包，可安全发布
作者：cc
创建时间：2025-01-20
"""

import zipapp
import os
import shutil
import glob
import fnmatch
from pathlib import Path

# --- 配置 ---
# 项目根目录
source_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# 输出的 app.pyz 文件路径
target_file = os.path.join(os.path.dirname(__file__), 'release', 'ft_data_cleaner.pyz')
# 打包的入口点
main_entry_point = 'gui.ft_data_cleaner_gui:main'
# 需要包含在 .pyz 文件中的顶层目录
packages_to_include = ['dc_processing', 'dvds_processing', 'rg_processing', 'gui']
# 需要包含在 .pyz 文件中的根目录下的 .py 文件
files_to_include = [
    'excel_utils.py',
]

# 🛡️ 安全设置：需要排除的敏感文件和目录
EXCLUDE_PATTERNS = [
    '*.md',           # 所有markdown文档
    '*.MD',           # 大写的markdown文档
    '*.log',          # 日志文件
    '*.txt',          # 文本文件(除了requirements.txt)
    'README*',        # README文件
    '*_plan.md',      # 计划文档
    '*-plan.md',      # 计划文档
    'todo_*.md',      # TODO文档
    'project-status.md',
    'PERFORMANCE_OPTIMIZATION_REPORT.md',
    '__pycache__',    # Python缓存目录
    '*.pyc',          # Python编译文件
    '*.pyo',          # Python优化文件
    '.git*',          # Git相关文件
    'test_*',         # 测试文件
    '*_test.py',      # 测试文件
    '*.bat',          # 批处理文件
    'sample/',        # 示例数据目录
    'ASEData/',       # 测试数据目录
    'output/',        # 输出目录
    'packaging/',     # 打包目录本身
]

def should_exclude_file(file_path):
    """检查文件是否应该被排除"""
    file_name = os.path.basename(file_path)
    rel_path = os.path.relpath(file_path, source_root)
    
    # 保留requirements.txt
    if file_name == 'requirements.txt':
        return False
    
    # 检查排除模式
    for pattern in EXCLUDE_PATTERNS:
        if '*' in pattern:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
        elif pattern in file_name or pattern in rel_path:
            return True
    
    return False

def copy_directory_filtered(src, dst):
    """复制目录，但过滤掉敏感文件"""
    if not os.path.exists(dst):
        os.makedirs(dst)
    
    excluded_count = 0
    included_count = 0
    
    for root, dirs, files in os.walk(src):
        # 过滤目录
        dirs[:] = [d for d in dirs if not should_exclude_file(os.path.join(root, d))]
        
        for file in files:
            src_file = os.path.join(root, file)
            
            if should_exclude_file(src_file):
                excluded_count += 1
                print(f"  ❌ 排除敏感文件: {os.path.relpath(src_file, src)}")
                continue
            
            # 计算目标路径
            rel_path = os.path.relpath(src_file, src)
            dst_file = os.path.join(dst, rel_path)
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            
            # 复制文件
            shutil.copy2(src_file, dst_file)
            included_count += 1
    
    return included_count, excluded_count

def create_secure_archive():
    """创建安全的 ft_data_cleaner.pyz 文件（排除敏感信息）"""
    
    # 临时的打包源目录
    temp_source_dir = os.path.join(os.path.dirname(__file__), '_temp_secure_build_src')
    
    # 确保release目录存在
    release_dir = os.path.dirname(target_file)
    os.makedirs(release_dir, exist_ok=True)

    # 清理旧的临时目录和目标文件
    if os.path.exists(temp_source_dir):
        shutil.rmtree(temp_source_dir)
    if os.path.exists(target_file):
        os.remove(target_file)
        print(f"已删除旧的 {os.path.basename(target_file)}")

    os.makedirs(temp_source_dir, exist_ok=True)
    print(f"创建临时目录: {temp_source_dir}")

    total_included = 0
    total_excluded = 0

    # --- 拷贝必要的包到临时目录（带过滤） ---
    for package_name in packages_to_include:
        src_path = os.path.join(source_root, package_name)
        if os.path.isdir(src_path):
            dest_path = os.path.join(temp_source_dir, package_name)
            print(f"🔍 正在过滤并拷贝 {package_name}...")
            included, excluded = copy_directory_filtered(src_path, dest_path)
            total_included += included
            total_excluded += excluded
            print(f"  ✅ {package_name}: 包含 {included} 个文件，排除 {excluded} 个敏感文件")
        else:
            print(f"警告: 找不到目录 {package_name}，跳过。")
            
    # --- 拷贝必要的 .py 文件到临时目录 ---
    for file_name in files_to_include:
        src_path = os.path.join(source_root, file_name)
        if os.path.isfile(src_path):
            if should_exclude_file(src_path):
                print(f"  ❌ 排除敏感文件: {file_name}")
                total_excluded += 1
                continue
            
            dest_path = os.path.join(temp_source_dir, file_name)
            shutil.copy2(src_path, dest_path)
            print(f"  ✅ 已拷贝 {file_name}")
            total_included += 1
        else:
            print(f"警告: 找不到文件 {file_name}，跳过。")
    
    # --- 拷贝requirements.txt ---
    requirements_src = os.path.join(source_root, 'requirements.txt')
    if os.path.isfile(requirements_src):
        requirements_dest = os.path.join(temp_source_dir, 'requirements.txt')
        shutil.copy2(requirements_src, requirements_dest)
        print(f"  ✅ 已拷贝 requirements.txt")
        total_included += 1

    # --- 创建 .pyz 文件 ---
    print(f"\n🔒 正在创建安全的压缩包...")
    print(f"📊 统计: 包含 {total_included} 个文件，排除 {total_excluded} 个敏感文件")
    
    zipapp.create_archive(
        source=temp_source_dir,
        target=target_file,
        interpreter='/usr/bin/env python',
        main=main_entry_point,
        compressed=True
    )
    print(f"🎉 成功创建安全版本: {target_file}")

    # 显示文件大小
    if os.path.exists(target_file):
        file_size = os.path.getsize(target_file)
        print(f"📁 文件大小: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")

    # --- 清理临时目录 ---
    shutil.rmtree(temp_source_dir)
    print(f"🧹 已删除临时目录: {temp_source_dir}")

def create_usage_instructions():
    """创建使用说明文件"""
    usage_file = os.path.join(os.path.dirname(target_file), 'USAGE.txt')
    
    usage_content = """FT数据清洗工具 - 使用说明

运行方式：
1. 确保系统已安装Python 3.6或更高版本
2. 安装依赖：pip install -r requirements.txt
3. 运行程序：python ft_data_cleaner.pyz

程序功能：
- DC数据清洗：处理DC测试数据
- DVDS数据清洗：处理DVDS测试数据  
- RG数据清洗：处理RG测试数据

注意事项：
- 请确保输入数据格式正确
- 输出文件将保存在指定的输出目录
- 如遇问题请查看程序日志信息

版本：1.2
作者：cc
"""
    
    with open(usage_file, 'w', encoding='utf-8') as f:
        f.write(usage_content)
    
    print(f"📝 已创建使用说明: {usage_file}")

if __name__ == '__main__':
    print("🛡️  开始创建FT数据清洗工具安全版本...")
    print("=" * 60)
    create_secure_archive()
    create_usage_instructions()
    print("=" * 60)
    print("🎯 安全打包完成！")
    print("💡 提示: 当前版本已移除敏感文档，可安全发布")
    print(f"📦 输出文件: {target_file}") 