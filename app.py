import streamlit as st
import fitz
import zipfile
import io

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

def resize_pdf_stream(input_bytes, target_w_mm, target_h_mm, margin_mm=2):
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
        
        # 等比例缩放计算
        scale = min(avail_w / content_bbox.width, avail_h / content_bbox.height)
        
        new_w = content_bbox.width * scale
        new_h = content_bbox.height * scale
        
        # 居中坐标计算
        dx = (target_w_pts - new_w) / 2
        dy = (target_h_pts - new_h) / 2
        
        target_rect = fitz.Rect(dx, dy, dx + new_w, dy + new_h)
        
        new_page = dest_doc.new_page(width=target_w_pts, height=target_h_pts)
        new_page.show_pdf_page(target_rect, src_doc, page.number, clip=content_bbox)

    pdf_bytes = dest_doc.write()
    dest_doc.close()
    src_doc.close()
    
    return pdf_bytes

# ============ 网页 UI 设计 ============
st.set_page_config(page_title="PDF 标签批量转换器", page_icon="🏷️")

st.title("🏷️ PDF 标签尺寸批量转换器")
st.write("上传标签 PDF（支持一次性拖入多个），系统会自动等比例缩放居中，并打包成 ZIP 供你一键下载。")

# 尺寸选择器
size_option = st.radio(
    "📏 请选择目标标签物理尺寸：",
    ("50 x 30 mm (常规标签)", "70 x 40 mm (大标签)", "自定义尺寸")
)

# 动态设定长宽
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

# 高级设置
with st.expander("⚙️ 高级设置"):
    margin = st.number_input("边缘留白安全区 (mm) - 防止打印机把边框切掉", min_value=0.0, value=2.0, step=0.5)

# 核心修改点：允许上传多个文件 (accept_multiple_files=True)
uploaded_files = st.file_uploader("📥 请选择要处理的 PDF 文件（可多选）", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.info(f"📁 已准备就绪 {len(uploaded_files)} 个文件。")
    
    if st.button("🚀 开始批量转换", type="primary"):
        with st.spinner('正在火速批量处理中，请稍候...'):
            try:
                # 在内存中创建一个 ZIP 压缩包
                zip_buffer = io.BytesIO()
                
                # 开始打包
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for file in uploaded_files:
                        input_bytes = file.read()
                        
                        # 转换单个 PDF
                        output_bytes = resize_pdf_stream(input_bytes, target_w, target_h, margin)
                        
                        # 把转换后的 PDF 塞进 ZIP 包里
                        new_filename = f"转换_{int(target_w)}x{int(target_h)}_{file.name}"
                        zip_file.writestr(new_filename, output_bytes)
                
                st.success(f"✅ 成功转换并打包了 {len(uploaded_files)} 个文件！")
                
                # 提供 ZIP 打包下载
                st.download_button(
                    label=f"📦 ⬇️ 一键下载全部转换结果 (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"批量标签转换结果_{int(target_w)}x{int(target_h)}mm.zip",
                    mime="application/zip"
                )
            except Exception as e:
                st.error(f"处理失败，错误信息: {str(e)}")
