# =========================================
        logo = logo.resize((int(logo.width*ratio), 300), Image.Resampling.LANCZOS)
        bg.paste(logo, (40, 28), logo)
    except Exception:
        pass


    # ===== Chart SLA rata-rata per proses =====
    # Siapkan chart matplotlib (transparan) dan tempel ke poster
    processes = list(sla_text_dict.keys())
    sla_days = [sla_text_dict[p]['average_days'] for p in processes] if processes else []
    fig, ax = plt.subplots(figsize=(10, 4), dpi=200)  # resolusi tinggi
    if processes:
        ax.bar(processes, sla_days)
    ax.set_ylabel('Hari')
    ax.set_title('Rata-rata SLA per Proses')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    buf_chart = io.BytesIO()
    fig.savefig(buf_chart, format='PNG', transparent=True)
    buf_chart.seek(0)
    chart_img = Image.open(buf_chart)
    chart_x, chart_y = left_margin, 320
    bg.paste(chart_img, (chart_x, chart_y), chart_img)

    # ===== Kartu Tabel SLA =====
    card1_x0, card1_y0 = left_margin, 900
    card1_x1, card1_y1 = W - 140, 900 + 520
    draw_card_with_shadow(bg, (card1_x0, card1_y0, card1_x1, card1_y1),
                          radius=32, shadow=28, fill=(255,255,255), outline=(210,210,210), outline_width=2)
    # Header gradient
    header_h = 72
    draw_gradient_bar(bg, (card1_x0, card1_y0, card1_x1, card1_y0+header_h),
                      top_color=(79,129,189), bottom_color=(31,87,163))
    draw.text((card1_x0+24, card1_y0+18), "SLA PER PROSES", font=font_h, fill=(255,255,255))

    # Kolom
    col1_w, col2_w = 560, (card1_x1 - card1_x0 - 560 - 60)
    table_left = card1_x0 + 30
    table_top  = card1_y0 + header_h + 20
    row_h = 60

    # Header kolom
    draw.text((table_left, table_top), "PROSES", font=font_h, fill=(40,40,40))
    draw.text((table_left + col1_w, table_top), "RATA-RATA SLA", font=font_h, fill=(40,40,40))
    y_cursor = table_top + 18 + 24

    # Garis pemisah header
    draw.line([(card1_x0+20, y_cursor), (card1_x1-20, y_cursor)], fill=(220,220,220), width=2)
    y = y_cursor + 18

    # Isi baris
    for i, (p, info) in enumerate(sla_text_dict.items()):
        row_bg = Image.new("RGBA", (card1_x1-card1_x0-40, row_h), (255,255,255,0))
        row_draw = ImageDraw.Draw(row_bg)
        if i % 2 == 0:
            # subtle zebra
            row_draw.rectangle([0,0,row_bg.width,row_bg.height], fill=(245,248,253,255))
        # teks
        row_draw.text((10, 12), str(p), font=font_cell, fill=(30,30,30))
        row_draw.text((10 + col1_w, 12), str(info['text']), font=font_cell, fill=(30,30,30))
        bg.paste(row_bg, (card1_x0+20, y), row_bg)
        y += row_h + 8

    # ===== Kartu Tabel Jumlah Transaksi =====
    card2_x0, card2_y0 = left_margin, card1_y1 + 60
    card2_x1, card2_y1 = W - 140, card2_y0 + 520
    draw_card_with_shadow(bg, (card2_x0, card2_y0, card2_x1, card2_y1),
                          radius=32, shadow=28, fill=(255,255,255), outline=(210,210,210), outline_width=2)
