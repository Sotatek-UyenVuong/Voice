#!/usr/bin/env python3
"""
Script để cắt ảnh avatar 6 frames thành 6 files riêng biệt
Ảnh gốc có 6 bánh bao xếp thành 2 hàng x 3 cột
"""

from PIL import Image
import os

def split_avatar_frames(input_image_path, output_dir):
    """
    Cắt ảnh 6 frames thành 6 files riêng
    
    Layout: 2 hàng x 3 cột
    [0] [1] [2]
    [3] [4] [5]
    """
    
    # Tạo output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load ảnh gốc
    img = Image.open(input_image_path)
    width, height = img.size
    
    print(f"📸 Ảnh gốc: {width}x{height}")
    
    # Tính kích thước mỗi frame
    frame_width = width // 3
    frame_height = height // 2
    
    print(f"✂️  Mỗi frame: {frame_width}x{frame_height}")
    
    # Frame positions: [row][col]
    positions = [
        (0, 0), (0, 1), (0, 2),  # Hàng 1
        (1, 0), (1, 1), (1, 2),  # Hàng 2
    ]
    
    # Cắt và lưu từng frame
    for idx, (row, col) in enumerate(positions):
        # Tính tọa độ crop
        left = col * frame_width
        top = row * frame_height
        right = left + frame_width
        bottom = top + frame_height
        
        # Crop frame
        frame = img.crop((left, top, right, bottom))
        
        # Lưu file
        output_path = os.path.join(output_dir, f"mouth_{idx}.png")
        frame.save(output_path, "PNG")
        
        print(f"✅ Saved: mouth_{idx}.png ({frame.size[0]}x{frame.size[1]})")
    
    # Tạo base.png (frame đầu tiên làm base - có thể customize sau)
    base_frame = img.crop((0, 0, frame_width, frame_height))
    base_path = os.path.join(output_dir, "base.png")
    base_frame.save(base_path, "PNG")
    print(f"✅ Saved: base.png (base avatar)")
    
    print(f"\n🎉 Hoàn thành! Đã tạo {len(positions)} mouth frames + 1 base")
    print(f"📁 Output: {output_dir}")
    print("\n💡 Tiếp theo:")
    print(f"   1. Copy folder '{output_dir}' vào 'web-client-react/public/avatar/'")
    print(f"   2. Sử dụng AnimatedAvatar component trong App.jsx")


def create_spritesheet_alternative(input_image_path, output_path):
    """
    Alternative: Tạo vertical spritesheet (1 cột x 6 hàng)
    Tối ưu cho CSS animations
    """
    img = Image.open(input_image_path)
    width, height = img.size
    
    frame_width = width // 3
    frame_height = height // 2
    
    # Create new vertical image
    spritesheet = Image.new('RGBA', (frame_width, frame_height * 6))
    
    positions = [
        (0, 0), (0, 1), (0, 2),  # Hàng 1
        (1, 0), (1, 1), (1, 2),  # Hàng 2
    ]
    
    for idx, (row, col) in enumerate(positions):
        left = col * frame_width
        top = row * frame_height
        right = left + frame_width
        bottom = top + frame_height
        
        frame = img.crop((left, top, right, bottom))
        spritesheet.paste(frame, (0, idx * frame_height))
    
    spritesheet.save(output_path, "PNG")
    print(f"✅ Created spritesheet: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════╗
║           Avatar Frame Splitter Tool                     ║
╚══════════════════════════════════════════════════════════╝

Usage:
    python3 split_avatar_frames.py <input_image> [output_dir]

Arguments:
    input_image    - Path to 6-frame avatar image (2x3 grid)
    output_dir     - Output directory (default: ./avatar_frames)

Example:
    python3 split_avatar_frames.py avatar_6frames.png ./output

Optional - Create vertical spritesheet:
    python3 split_avatar_frames.py avatar_6frames.png ./output --spritesheet
""")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./avatar_frames"
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)
    
    # Check for spritesheet flag
    if "--spritesheet" in sys.argv:
        spritesheet_path = os.path.join(output_dir, "mouth_spritesheet.png")
        os.makedirs(output_dir, exist_ok=True)
        create_spritesheet_alternative(input_path, spritesheet_path)
    else:
        split_avatar_frames(input_path, output_dir)

