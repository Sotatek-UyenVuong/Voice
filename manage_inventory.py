#!/usr/bin/env python3
"""
Script quản lý inventory - View và Reset số lượng sản phẩm
"""

import json
from pathlib import Path
import sys

INVENTORY_FILE = "/home/sotatek/Documents/Uyen/demo_voice/inventory.json"

def view_inventory():
    """Xem inventory hiện tại"""
    if not Path(INVENTORY_FILE).exists():
        print(f"❌ File {INVENTORY_FILE} không tồn tại")
        return
    
    try:
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            inventory = json.load(f)
        
        print("\n📦 INVENTORY HIỆN TẠI:")
        print("=" * 50)
        for key, item in inventory.items():
            status = "✅" if item['quantity'] > 0 else "❌"
            print(f"{status} {item['name']}: ${item['price']} - Còn {item['quantity']} phần")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")


def reset_inventory():
    """Reset inventory về số lượng mặc định"""
    default_inventory = {
        "pizza": {
            "name": "Pizza",
            "price": 10.0,
            "quantity": 10
        },
        "salad": {
            "name": "Salad",
            "price": 5.0,
            "quantity": 10
        },
        "ice cream": {
            "name": "Ice Cream",
            "price": 3.0,
            "quantity": 20
        },
        "coffee": {
            "name": "Coffee",
            "price": 2.0,
            "quantity": 10
        }
    }
    
    try:
        with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_inventory, f, ensure_ascii=False, indent=2)
        
        print("\n✅ Đã reset inventory về số lượng mặc định!")
        view_inventory()
        
    except Exception as e:
        print(f"❌ Lỗi khi reset inventory: {e}")


def update_quantity(item_name: str, new_quantity: int):
    """Cập nhật số lượng của một sản phẩm"""
    if not Path(INVENTORY_FILE).exists():
        print(f"❌ File {INVENTORY_FILE} không tồn tại")
        return
    
    try:
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            inventory = json.load(f)
        
        item_key = item_name.lower()
        if item_key not in inventory:
            print(f"❌ Không tìm thấy sản phẩm '{item_name}'")
            print(f"Các sản phẩm có sẵn: {', '.join([v['name'] for v in inventory.values()])}")
            return
        
        old_quantity = inventory[item_key]['quantity']
        inventory[item_key]['quantity'] = new_quantity
        
        with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã cập nhật {inventory[item_key]['name']}: {old_quantity} → {new_quantity} phần")
        view_inventory()
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật: {e}")


def main():
    if len(sys.argv) < 2:
        print("\n🛠️  QUẢN LÝ INVENTORY - RESTAURANT AGENT")
        print("=" * 50)
        print("Sử dụng:")
        print("  python manage_inventory.py view              - Xem inventory")
        print("  python manage_inventory.py reset             - Reset về mặc định")
        print("  python manage_inventory.py update <tên> <số> - Cập nhật số lượng")
        print("\nVí dụ:")
        print("  python manage_inventory.py view")
        print("  python manage_inventory.py reset")
        print("  python manage_inventory.py update Pizza 50")
        print("=" * 50)
        return
    
    command = sys.argv[1].lower()
    
    if command == "view":
        view_inventory()
    
    elif command == "reset":
        confirm = input("⚠️  Bạn có chắc muốn reset inventory? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            reset_inventory()
        else:
            print("❌ Đã hủy")
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("❌ Thiếu tham số. Sử dụng: python manage_inventory.py update <tên> <số>")
            return
        
        item_name = sys.argv[2]
        try:
            quantity = int(sys.argv[3])
            if quantity < 0:
                print("❌ Số lượng phải >= 0")
                return
            update_quantity(item_name, quantity)
        except ValueError:
            print("❌ Số lượng phải là số nguyên")
    
    else:
        print(f"❌ Lệnh không hợp lệ: {command}")
        print("Các lệnh có sẵn: view, reset, update")


if __name__ == "__main__":
    main()

