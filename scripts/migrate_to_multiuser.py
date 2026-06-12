#!/usr/bin/env python3
"""
数据迁移脚本：单用户 → 多用户

功能：
1. 为 users 表添加 role 字段
2. 将现有用户（id=1）设为 admin 角色
3. 验证迁移结果

用法：
  cd backend && python ../scripts/migrate_to_multiuser.py

注意：后端启动时会自动执行此迁移（_migrate_db），此脚本供手动执行或验证使用。
"""

import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.database import engine, SessionLocal
from app.models import User


def migrate():
    """执行迁移：添加 role 字段并设置现有用户为 admin。"""
    print("🔄 开始迁移：单用户 → 多用户")
    print()

    # 检查 users 表是否存在
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "users" not in tables:
        print("ℹ️  users 表不存在，跳过迁移（首次运行，建表时会自动包含 role 字段）")
        return

    # 检查 role 列是否已存在
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "role" in columns:
        print("✅ role 字段已存在，跳过添加")
    else:
        print("📝 添加 role 字段到 users 表...")
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            )
        print("✅ role 字段添加成功")

    # 将 id=1 的用户设为 admin（与 _migrate_db 逻辑一致）
    print()
    print("📝 将首个用户 (id=1) 设为 admin 角色...")
    db = SessionLocal()
    try:
        first_user = db.query(User).filter(User.id == 1).first()
        if first_user:
            if first_user.role != "admin":
                first_user.role = "admin"
                print(f"   - 用户 '{first_user.username}' (id=1) → admin")
            else:
                print(f"   - 用户 '{first_user.username}' (id=1) 已是 admin，跳过")
        else:
            print("   - 未找到 id=1 的用户，跳过")
        db.commit()
    finally:
        db.close()

    # 验证结果
    print()
    print("🔍 验证迁移结果...")
    db = SessionLocal()
    try:
        first_user = db.query(User).filter(User.id == 1).first()
        if first_user:
            status_icon = "✅" if first_user.role == "admin" else "❌"
            print(f"   {status_icon} {first_user.username} (id=1, role={first_user.role})")
        else:
            print("⚠️  未找到 id=1 的用户")
        user_count = db.query(User).count()
        print(f"   📊 总用户数: {user_count}")
    finally:
        db.close()

    print()
    print("🎉 迁移完成！")


if __name__ == "__main__":
    migrate()
