import streamlit as st
import fitz
import io

def get_content_bbox(page):
    """提取页面内所有真实内容的边界框"""
    rects = []
    blocks = page.get_text("blocks")
    for b in blocks:
        rects.append(fitz.Rect(b[:4]))
        
    drawings = page.get_drawings()
    for d in drawings:
        rects.append(d["rect"])
        
    if not rects:
        return fitz.Rect()
        
    bbox = rects[0]
    for r in rects[1:]:
        bbox |= r
        
    return bbox

def center_pdf_stream(input_bytes):
    """在内存中处理 PDF 并返回处理后的字节流"""
    # 从内存读取 PDF
    src_doc = fitz.open(stream=input_bytes, filetype="pdf")
    dest_doc = fitz.open()

    for i, page in enumerate(src_doc):
        rect = page.rect
        content_bbox = get_content_bbox(page)
        
        if content_bbox.is_empty or content_bbox.width == 0:
            content_bbox = rect

        new_page = dest_doc.new_page(width=rect.width, height=rect.height)
        
        dx = (rect.width - content_bbox.width) / 2
        dy = (rect.height - content_bbox.height) / 2
        target_rect = fitz.Rect(dx, dy, dx + content_bbox.width, dy + content_bbox.height)

        new_page.show_pdf_page(target_rect, src_doc, page.number, clip=content_bbox)

    # 将新文档写入内存
    pdf_bytes = dest_doc.write()
    dest_doc.close()
    src_doc.close()
    
    return pdf_bytes

# ============ 网页 UI 设计 ============
st.set_page_config(page_title="PDF 标签智能居中工具", page_icon="📄")

st.title("📄 PDF 标签智能居中工具")
st.write("上传你的条码或面单 PDF，系统会自动识别内容并将其置于 A4 纸正中心。")

uploaded_file = st.file_uploader("请选择要处理的 PDF 文件", type=["pdf"])

if uploaded_file is not None:
    st.info("文件上传成功！点击下方按钮开始处理。")
    
    if st.button("🚀 开始智能居中", type="primary"):
        with st.spinner('正在处理中，请稍候...'):
            try:
                # 获取上传文件的字节流
                input_bytes = uploaded_file.read()
                
                # 执行居中处理
                output_bytes = center_pdf_stream(input_bytes)
                
                st.success("✅ 处理完成！")
                
                # 提供下载按钮
                st.download_button(
                    label="⬇️ 下载居中后的 PDF",
                    data=output_bytes,
                    file_name=f"居中_{uploaded_file.name}",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"处理失败，错误信息: {str(e)}")