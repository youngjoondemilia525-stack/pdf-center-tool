import streamlit as st
import fitz

def get_content_bbox(page):
    """提取页面内所有真实内容的边界框"""
    rects = []
    for b in page.get_text("blocks"):
        rects.append(fitz.Rect(b[:4]))
    for d in page.get_drawings():
        rects.append(d["rect"])
    for img in page.get_image_info():
        rects.append(fitz.Rect(img["bbox"]))
        
    if not rects:
        return fitz.Rect()
        
    bbox = rects[0]
    for r in rects[1:]:
        bbox |= r
    return bbox

def resize_pdf_stream(input_bytes, target_w_mm, target_h_mm, margin_mm=2, stretch=False, zoom_factor=1.0):
    """在内存中将 PDF 缩放居中到指定毫米尺寸，并返回字节流"""
    MM_TO_PTS = 72 / 25.4
    
    target_w_pts = target_w_mm * MM_TO_PTS
    target_h_pts = target_h_mm * MM_TO_PTS
    margin_pts = margin_mm * MM_TO_PTS

    src_doc = fitz.open(stream=input_bytes, filetype="pdf")
    dest_doc = fitz.open()

    for i, page in enumerate(src_doc):
        content_bbox = get_content_bbox(page)
        if content_bbox.is_empty or content_bbox.width == 0:
            content_bbox = page.rect
            
        avail_w = target_w_pts - 2 * margin_pts
        avail_h = target_h_pts - 2 * margin_pts
        
        if stretch:
            # 强制铺满可用空间（拉伸）
            box_w = avail_w
            box_h = avail_h
            keep_prop = False
        else:
            # 等比例缩放（可能会留白边）
            scale = min(avail_w / content_bbox.width, avail_h / content_bbox.height)
            box_w = content_bbox.width * scale
            box_h = content_bbox.height * scale
            keep_prop = True
            
        # 应用用户的额外放大系数
        final_w = box_w * zoom_factor
        final_h = box_h * zoom_factor
        
        # 核心：无论怎么放大，绝对不允许超过纸张物理边界！
        if final_w > target_w_pts: final_w = target_w_pts
        if final_h > target_h_pts: final_h = target_h_pts
        
        # 重新计算居中
        dx = (target_w_pts - final_w) / 2
        dy = (target_h_pts - final_h) / 2
        
        target_rect = fitz.Rect(dx, dy, dx + final_w, dy + final_h)
        
        new_page = dest_doc.new_page(width=target_w_pts, height=target_h_pts)
        
        # 写入新页面，受 keep_proportion 控制是否拉伸
        new_page.show_pdf_page(target_rect, src_doc, page.number, clip=content_bbox, keep_proportion=keep_prop)

    pdf_bytes = dest_doc.write()
    dest_doc.close()
    src_doc.close()
    
    return pdf_bytes

# ============ 网页 UI 设计 ============
st.set_page_config(page_title="PDF 标签尺寸转换器", page_icon="🏷️")

st.title("🏷️ PDF 标签尺寸智能转换器")
st.write("上传标签 PDF，系统会自动提取内容并转换到指定尺寸。")

# 尺寸选择器
size_option = st.radio(
    "📏 请选择目标标签物理尺寸：",
    ("50 x 30 mm (常规标签)", "70 x 40 mm (大标签)", "自定义尺寸"),
    horizontal=True
)

if size_option == "50 x 30 mm (常规标签)":
    target_w, target_h = 50.0, 30.0
elif size_option == "70 x 40 mm (大标签)":
    target_w, target_h = 70.0, 40.0
else:
    col1, col2 = st.columns(2)
    with col1:
        target_w = st.number_input("宽度 (mm)", min_value=10.0, value=100.0, step=1.0)
    with col2:
        target_h = st.number_input("高度 (mm)", min_value=10.0, value=30.0, step=1.0)

# ============ 新增功能区域 ============
st.markdown("---")
st.subheader("🔍 放大与排版设置")

layout_mode = st.radio(
    "排版模式（觉得字小，推荐选拉伸铺满）：",
    ("保持原比例 (可能两侧留白)", "拉伸铺满 (填满标签，字变大，不影响扫码)"),
    horizontal=True
)
is_stretch = True if layout_mode == "拉伸铺满 (填满标签，字变大，不影响扫码)" else False

zoom_val = st.slider("微调放大系数 (无论怎么放大都不会超过纸张边界)", min_value=1.0, max_value=1.5, value=1.0, step=0.05)

with st.expander("⚙️ 高级设置"):
    margin = st.number_input("边缘留白安全区 (mm) - 若想字更大，可调小至 0 或 1", min_value=0.0, value=2.0, step=0.5)
st.markdown("---")

uploaded_file = st.file_uploader("📥 请选择要处理的 PDF 文件", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 开始转换", type="primary"):
        with st.spinner('正在处理中，请稍候...'):
            try:
                input_bytes = uploaded_file.read()
                
                output_bytes = resize_pdf_stream(input_bytes, target_w, target_h, margin, is_stretch, zoom_val)
                
                st.success("✅ 转换成功！")
                
                st.download_button(
                    label=f"⬇️ 下载 {int(target_w)}x{int(target_h)}mm 的新 PDF",
                    data=output_bytes,
                    file_name=f"转换_{int(target_w)}x{int(target_h)}_{uploaded_file.name}",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"处理失败，错误信息: {str(e)}")
