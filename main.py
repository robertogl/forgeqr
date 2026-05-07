import base64
import io
import os
import re
import secrets
import string
from datetime import datetime

import httpx
import qrcode
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, text
from fastapi.responses import PlainTextResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import AppRedirect, ContactMessage, DynamicQR, Feedback, PageVisit, QRScan, SiteStats, Testimonial

load_dotenv()

app = FastAPI(title="Forge QR")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8002")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qr_codes.db")

DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
    "gapped": GappedSquareModuleDrawer,
    "vertical": VerticalBarsDrawer,
    "horizontal": HorizontalBarsDrawer,
}

EYE_DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
}

FONTS = {
    "arial":      ["arial.ttf",      "C:/Windows/Fonts/arial.ttf"],
    "georgia":    ["georgia.ttf",    "C:/Windows/Fonts/georgia.ttf"],
    "verdana":    ["verdana.ttf",    "C:/Windows/Fonts/verdana.ttf"],
    "trebuchet":  ["trebuc.ttf",     "C:/Windows/Fonts/trebuc.ttf"],
    "courier":    ["cour.ttf",       "C:/Windows/Fonts/cour.ttf"],
    "times":      ["times.ttf",      "C:/Windows/Fonts/times.ttf"],
    "calibri":    ["calibri.ttf",    "C:/Windows/Fonts/calibri.ttf"],
    "cambria":    ["cambria.ttc",    "C:/Windows/Fonts/cambria.ttc"],
    "comic":      ["comic.ttf",      "C:/Windows/Fonts/comic.ttf"],
    "impact":     ["impact.ttf",     "C:/Windows/Fonts/impact.ttf"],
    "tahoma":     ["tahoma.ttf",     "C:/Windows/Fonts/tahoma.ttf"],
    "palatino":   ["pala.ttf",       "C:/Windows/Fonts/pala.ttf"],
    "segoeui":    ["segoeui.ttf",    "C:/Windows/Fonts/segoeui.ttf"],
    "candara":    ["Candara.ttf",    "C:/Windows/Fonts/Candara.ttf"],
    "constantia": ["constan.ttf",    "C:/Windows/Fonts/constan.ttf"],
    "corbel":     ["corbel.ttf",     "C:/Windows/Fonts/corbel.ttf"],
}

def _apply_effect(img: Image.Image, effect: str) -> Image.Image:
    if effect == "flat" or not effect:
        return img
    img = img.convert("RGBA")
    w, h = img.size
    alpha = img.split()[3]
    if effect == "shadow":
        offset, blur = 10, 8
        shadow_canvas = Image.new("RGBA", (w + offset, h + offset), (0, 0, 0, 0))
        shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shadow_color = Image.new("RGBA", (w, h), (0, 0, 0, 160))
        shadow_layer.paste(shadow_color, mask=alpha)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur))
        shadow_canvas.paste(shadow_layer, (offset, offset))
        shadow_canvas.paste(img, (0, 0), mask=alpha)
        return shadow_canvas
    if effect == "3d":
        pad = 22
        s_off, g_off = 10, 8   # shadow drops down, glow rises up
        pw, ph = w + pad * 2, h + pad * 2
        result = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        # Dark shadow below
        sh = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        sh_face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh_face.paste(Image.new("RGBA", (w, h), (0, 0, 0, 190)), mask=alpha)
        sh.paste(sh_face, (pad, pad + s_off))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        result = Image.alpha_composite(result, sh)
        # Warm glow above
        gl = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        gl_face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gl_face.paste(Image.new("RGBA", (w, h), (255, 240, 180, 160)), mask=alpha)
        gl.paste(gl_face, (pad, pad - g_off))
        gl = gl.filter(ImageFilter.GaussianBlur(12))
        result = Image.alpha_composite(result, gl)
        # QR face centered
        face = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        face.paste(img, (pad, pad), mask=alpha)
        # Erase any glow/shadow that bled inside the face boundary, then place face on top
        result.paste(Image.new("RGBA", (pw, ph), (0, 0, 0, 0)), mask=face.split()[3])
        result = Image.alpha_composite(result, face)
        return result
    return img


def _load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS.get(font_name, FONTS["arial"]):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


@app.on_event("startup")
async def startup():
    init_db()


def _short_code(length: int = 8) -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def _parse_ua(ua: str):
    ua_l = ua.lower()
    # Device
    if any(k in ua_l for k in ("iphone", "android", "mobile", "blackberry", "windows phone")):
        device = "Mobile"
    elif any(k in ua_l for k in ("ipad", "tablet")):
        device = "Tablet"
    else:
        device = "Desktop"
    # OS
    if "windows nt" in ua_l:
        os_name = "Windows"
    elif "iphone" in ua_l or "ipad" in ua_l:
        os_name = "iOS"
    elif "android" in ua_l:
        os_name = "Android"
    elif "mac os" in ua_l or "macos" in ua_l:
        os_name = "macOS"
    elif "linux" in ua_l:
        os_name = "Linux"
    else:
        os_name = "Other"
    # Browser
    if "edg/" in ua_l or "edge/" in ua_l:
        browser = "Edge"
    elif "opr/" in ua_l or "opera" in ua_l:
        browser = "Opera"
    elif "chrome/" in ua_l:
        browser = "Chrome"
    elif "firefox/" in ua_l:
        browser = "Firefox"
    elif "safari/" in ua_l:
        browser = "Safari"
    else:
        browser = "Other"
    return device, os_name, browser


async def _geolocate(ip: str):
    if not ip or ip in ("127.0.0.1", "::1"):
        return None, None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}?fields=country,city,status")
            data = r.json()
            if data.get("status") == "success":
                return data.get("country"), data.get("city")
    except Exception:
        pass
    return None, None


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _add_frame(img: Image.Image, text: str, fg_rgb: tuple, bg_rgb: tuple, container_shape: str = "square", text_color_rgb: tuple | None = None, font_name: str = "arial") -> Image.Image:
    text_rgb = text_color_rgb if text_color_rgb is not None else fg_rgb
    padding = 20
    text_area_h = 52
    qr_w, qr_h = img.size
    new_w = qr_w + padding * 2
    new_h = qr_h + padding * 2 + text_area_h
    frame = Image.new("RGBA", (new_w, new_h), bg_rgb + (255,))
    draw = ImageDraw.Draw(frame)
    frame.paste(img, (padding, padding))
    font = _load_font(font_name, 26)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_x = (new_w - (bbox[2] - bbox[0])) // 2
    text_y = qr_h + padding + (text_area_h - (bbox[3] - bbox[1])) // 2
    draw.text((text_x, text_y), text, fill=text_rgb + (255,), font=font)
    return frame


def _apply_container_shape(img: Image.Image, shape: str, bg_rgb: tuple, frame_text: str = "", fg_rgb: tuple = (0, 0, 0), text_color_rgb: tuple | None = None, font_name: str = "arial") -> Image.Image:
    if shape == "square":
        return img
    w, h = img.size
    if shape == "circle":
        pad = int(min(w, h) * (0.14 if frame_text.strip() else 0.10))
    else:
        pad = int(min(w, h) * 0.01)
    padded_w, padded_h = w + pad * 2, h + pad * 2
    canvas = Image.new("RGBA", (padded_w, padded_h), bg_rgb + (255,))
    canvas.paste(img, (pad, pad))
    # For circle: draw text inside the bottom quiet zone before clipping
    if shape == "circle" and frame_text.strip():
        text_rgb = text_color_rgb if text_color_rgb is not None else fg_rgb
        cdraw = ImageDraw.Draw(canvas)
        font = _load_font(font_name, 22)
        bbox = cdraw.textbbox((0, 0), frame_text.strip(), font=font)
        tx = (padded_w - (bbox[2] - bbox[0])) // 2
        ty = padded_h - pad - (bbox[3] - bbox[1]) - 6
        cdraw.text((tx, ty), frame_text.strip(), fill=text_rgb + (255,), font=font)
    mask = Image.new("L", (padded_w, padded_h), 0)
    draw = ImageDraw.Draw(mask)
    if shape == "rounded":
        draw.rounded_rectangle([0, 0, padded_w - 1, padded_h - 1], radius=min(padded_w, padded_h) // 6, fill=255)
    elif shape == "circle":
        draw.ellipse([0, 0, padded_w - 1, padded_h - 1], fill=255)
    result = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
    result.paste(canvas, mask=mask)
    return result


def build_qr_image(
    data: str,
    fg: str = "#000000",
    bg: str = "#FFFFFF",
    logo_bytes: bytes | None = None,
    dot_style: str = "square",
    eye_style: str = "square",
    container_shape: str = "square",
    frame_text: str = "",
    edge_line: bool = False,
    edge_color: str = "#000000",
    edge_width: int = 2,
    frame_color: str = "#000000",
    frame_font: str = "arial",
    container_effect: str = "flat",
) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    fg_rgb = _hex_to_rgb(fg)
    bg_rgb = _hex_to_rgb(bg)
    drawer_cls = DRAWERS.get(dot_style, SquareModuleDrawer)
    eye_cls = EYE_DRAWERS.get(eye_style, SquareModuleDrawer)

    # Generate in grayscale then apply colors — more reliable than SolidFillColorMask
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer_cls(),
        eye_drawer=eye_cls(),
    ).convert("L")

    fg_layer = Image.new("RGBA", img.size, fg_rgb + (255,))
    bg_layer = Image.new("RGBA", img.size, bg_rgb + (255,))
    mask = img.point(lambda p: 255 if p < 128 else 0)
    bg_layer.paste(fg_layer, mask=mask)
    img = bg_layer

    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            qr_w, qr_h = img.size
            logo.thumbnail((qr_w // 6, qr_h // 6), Image.LANCZOS)
            pad = 6
            canvas = Image.new("RGB", (logo.width + pad * 2, logo.height + pad * 2), (255, 255, 255))
            canvas.paste(logo.convert("RGB"), (pad, pad), mask=logo.split()[3])
            pos = ((qr_w - canvas.width) // 2, (qr_h - canvas.height) // 2)
            img_rgb = img.convert("RGB")
            img_rgb.paste(canvas, pos)
            img = img_rgb.convert("RGBA")
        except Exception:
            pass

    if frame_text.strip() and container_shape != "circle":
        frame_color_rgb = _hex_to_rgb(frame_color)
        img = _add_frame(img, frame_text.strip(), fg_rgb, bg_rgb, container_shape, frame_color_rgb, frame_font)

    img = _apply_container_shape(img, container_shape, bg_rgb, frame_text, fg_rgb, _hex_to_rgb(frame_color), frame_font)

    if edge_line:
        edge_rgb = _hex_to_rgb(edge_color)
        w, h = img.size
        edge_draw = ImageDraw.Draw(img)
        inset = edge_width // 2
        if container_shape == "circle":
            edge_draw.ellipse([inset, inset, w - inset - 1, h - inset - 1], outline=edge_rgb + (255,), width=edge_width)
        elif container_shape == "rounded":
            radius = min(w, h) // 6
            edge_draw.rounded_rectangle([inset, inset, w - inset - 1, h - inset - 1], radius=radius, outline=edge_rgb + (255,), width=edge_width)
        else:
            edge_draw.rectangle([inset, inset, w - inset - 1, h - inset - 1], outline=edge_rgb + (255,), width=edge_width)

    img = _apply_effect(img, container_effect)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ── Pages ────────────────────────────────────────────────────────────────────

ADMIN_KEY = os.getenv("ADMIN_KEY", "")

@app.get("/ads.txt", include_in_schema=False)
def ads_txt():
    return PlainTextResponse("google.com, pub-5198883341858973, DIRECT, f08c47fec0942fa0\n")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    content = "User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: https://forgeqr.onrender.com/sitemap.xml\n"
    return PlainTextResponse(content)


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://forgeqr.onrender.com/</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return Response(content=content, media_type="application/xml")


@app.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    stats = db.query(SiteStats).filter(SiteStats.id == 1).first()
    if not stats:
        stats = SiteStats(id=1, visitor_count=0)
        db.add(stats)
    stats.visitor_count += 1
    db.add(PageVisit())
    db.commit()
    testimonials = db.query(Testimonial).filter(Testimonial.approved == 1).order_by(Testimonial.submitted_at.desc()).all()
    return templates.TemplateResponse("index.html", {"request": request, "visitor_count": stats.visitor_count, "testimonials": testimonials})


@app.post("/api/testimonial")
async def submit_testimonial(
    message: str = Form(...),
    name: str = Form(""),
    use_case: str = Form(""),
    db: Session = Depends(get_db),
):
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    db.add(Testimonial(
        message=message.strip()[:1000],
        name=name.strip()[:80] or None,
        use_case=use_case.strip()[:80] or None,
        approved=0,
    ))
    db.commit()
    return {"success": True}


@app.get("/admin/testimonial/{tid}/approve")
async def approve_testimonial(tid: int, key: str = "", db: Session = Depends(get_db)):
    if ADMIN_KEY and key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")
    t = db.query(Testimonial).filter(Testimonial.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    t.approved = 1
    db.commit()
    return RedirectResponse(url=f"/admin?key={key}", status_code=302)


@app.get("/admin/testimonial/{tid}/delete")
async def delete_testimonial(tid: int, key: str = "", db: Session = Depends(get_db)):
    if ADMIN_KEY and key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")
    t = db.query(Testimonial).filter(Testimonial.id == tid).first()
    if t:
        db.delete(t)
        db.commit()
    return RedirectResponse(url=f"/admin?key={key}", status_code=302)


@app.post("/api/feedback")
async def submit_feedback(
    message: str = Form(...),
    rating: int = Form(None),
    page: str = Form(""),
    db: Session = Depends(get_db),
):
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    db.add(Feedback(
        message=message.strip()[:2000],
        rating=rating if rating and 1 <= rating <= 5 else None,
        page=page.strip()[:64] or None,
    ))
    db.commit()
    return {"success": True}


@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/contact")
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.post("/api/contact")
async def submit_contact(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    if not name.strip() or not email.strip() or not message.strip():
        raise HTTPException(status_code=400, detail="All fields are required")
    db.add(ContactMessage(
        name=name.strip()[:120],
        email=email.strip()[:254],
        message=message.strip()[:3000],
    ))
    db.commit()
    return {"success": True}


@app.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/guide")
async def guide(request: Request):
    return templates.TemplateResponse("guide.html", {"request": request})


@app.get("/admin")
async def admin_stats(request: Request, key: str = "", db: Session = Depends(get_db)):
    if ADMIN_KEY and key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")

    total = db.query(func.count(PageVisit.id)).scalar()

    is_pg = not DATABASE_URL.startswith("sqlite")

    if is_pg:
        by_day = db.execute(text(
            "SELECT DATE(visited_at) as d, COUNT(*) as c FROM page_visits GROUP BY d ORDER BY d DESC LIMIT 30"
        )).fetchall()
        by_month = db.execute(text(
            "SELECT to_char(visited_at, 'YYYY-MM') as m, COUNT(*) as c FROM page_visits GROUP BY m ORDER BY m DESC LIMIT 24"
        )).fetchall()
        by_year = db.execute(text(
            "SELECT to_char(visited_at, 'YYYY') as y, COUNT(*) as c FROM page_visits GROUP BY y ORDER BY y DESC"
        )).fetchall()
    else:
        by_day = db.execute(text(
            "SELECT DATE(visited_at) as d, COUNT(*) as c FROM page_visits GROUP BY d ORDER BY d DESC LIMIT 30"
        )).fetchall()
        by_month = db.execute(text(
            "SELECT strftime('%Y-%m', visited_at) as m, COUNT(*) as c FROM page_visits GROUP BY m ORDER BY m DESC LIMIT 24"
        )).fetchall()
        by_year = db.execute(text(
            "SELECT strftime('%Y', visited_at) as y, COUNT(*) as c FROM page_visits GROUP BY y ORDER BY y DESC"
        )).fetchall()

    qr_total = db.query(func.count(DynamicQR.short_code)).scalar()
    qr_scans = db.query(func.sum(DynamicQR.scan_count)).scalar() or 0
    feedback = db.query(Feedback).order_by(Feedback.submitted_at.desc()).limit(50).all()
    contacts = db.query(ContactMessage).order_by(ContactMessage.submitted_at.desc()).limit(50).all()
    pending = db.query(Testimonial).filter(Testimonial.approved == 0).order_by(Testimonial.submitted_at.desc()).all()
    approved = db.query(Testimonial).filter(Testimonial.approved == 1).order_by(Testimonial.submitted_at.desc()).all()

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "total": total,
        "by_day": by_day,
        "by_month": by_month,
        "by_year": by_year,
        "qr_total": qr_total,
        "qr_scans": qr_scans,
        "feedback": feedback,
        "pending_testimonials": pending,
        "approved_testimonials": approved,
        "admin_key": key,
        "contacts": contacts,
    })


@app.get("/manage/{short_code}")
async def manage_page(request: Request, short_code: str, token: str, db: Session = Depends(get_db)):
    entry = db.query(DynamicQR).filter(DynamicQR.short_code == short_code).first()
    if not entry or entry.edit_token != token:
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    return templates.TemplateResponse(
        "manage.html",
        {"request": request, "entry": entry, "token": token,
         "redirect_url": f"{BASE_URL}/r/{short_code}", "base_url": BASE_URL},
    )


@app.get("/stats/{short_code}")
async def qr_stats(request: Request, short_code: str, token: str, db: Session = Depends(get_db)):
    entry = db.query(DynamicQR).filter(DynamicQR.short_code == short_code).first()
    if not entry or entry.edit_token != token:
        raise HTTPException(status_code=403, detail="Invalid or expired link")

    scans = db.query(QRScan).filter(QRScan.short_code == short_code).order_by(QRScan.scanned_at.desc()).all()

    # Aggregate by day (last 30 days)
    is_pg = not DATABASE_URL.startswith("sqlite")
    if is_pg:
        by_day = db.execute(text(
            "SELECT DATE(scanned_at) as d, COUNT(*) as c FROM qr_scans WHERE short_code = :sc "
            "GROUP BY d ORDER BY d DESC LIMIT 30"
        ), {"sc": short_code}).fetchall()
    else:
        by_day = db.execute(text(
            "SELECT DATE(scanned_at) as d, COUNT(*) as c FROM qr_scans WHERE short_code = :sc "
            "GROUP BY d ORDER BY d DESC LIMIT 30"
        ), {"sc": short_code}).fetchall()

    # Country breakdown
    countries = db.execute(text(
        "SELECT COALESCE(country, 'Unknown') as c, COUNT(*) as n FROM qr_scans WHERE short_code = :sc GROUP BY c ORDER BY n DESC LIMIT 10"
    ), {"sc": short_code}).fetchall()

    # Device breakdown
    devices = db.execute(text(
        "SELECT COALESCE(device, 'Unknown') as d, COUNT(*) as n FROM qr_scans WHERE short_code = :sc GROUP BY d ORDER BY n DESC"
    ), {"sc": short_code}).fetchall()

    # OS breakdown
    oses = db.execute(text(
        "SELECT COALESCE(os, 'Unknown') as o, COUNT(*) as n FROM qr_scans WHERE short_code = :sc GROUP BY o ORDER BY n DESC"
    ), {"sc": short_code}).fetchall()

    # Browser breakdown
    browsers = db.execute(text(
        "SELECT COALESCE(browser, 'Unknown') as b, COUNT(*) as n FROM qr_scans WHERE short_code = :sc GROUP BY b ORDER BY n DESC"
    ), {"sc": short_code}).fetchall()

    return templates.TemplateResponse("qr_stats.html", {
        "request": request,
        "entry": entry,
        "token": token,
        "scans": scans,
        "by_day": list(reversed(by_day)),
        "countries": countries,
        "devices": devices,
        "oses": oses,
        "browsers": browsers,
        "base_url": BASE_URL,
    })


# ── Redirects ─────────────────────────────────────────────────────────────────

@app.get("/r/{short_code}")
async def redirect_dynamic(short_code: str, request: Request, db: Session = Depends(get_db)):
    entry = db.query(DynamicQR).filter(DynamicQR.short_code == short_code).first()
    if not entry:
        raise HTTPException(status_code=404, detail="QR code not found")
    entry.scan_count += 1
    entry.last_scan = datetime.utcnow()

    ua = request.headers.get("user-agent", "")
    device, os_name, browser = _parse_ua(ua)
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    country, city = await _geolocate(ip)

    db.add(QRScan(
        short_code=short_code,
        scanned_at=datetime.utcnow(),
        country=country,
        city=city,
        device=device,
        os=os_name,
        browser=browser,
    ))
    db.commit()
    return RedirectResponse(url=entry.destination_url, status_code=302)


@app.get("/app/{short_code}")
async def redirect_app(short_code: str, request: Request, db: Session = Depends(get_db)):
    entry = db.query(AppRedirect).filter(AppRedirect.short_code == short_code).first()
    if not entry:
        raise HTTPException(status_code=404, detail="QR code not found")
    entry.scan_count += 1
    entry.last_scan = datetime.utcnow()
    db.commit()

    ua = request.headers.get("user-agent", "").lower()
    if "iphone" in ua or "ipad" in ua or "ipod" in ua or "mac os" in ua:
        target = entry.ios_url or entry.fallback_url or entry.android_url
    elif "android" in ua:
        target = entry.android_url or entry.fallback_url or entry.ios_url
    else:
        target = entry.fallback_url or entry.ios_url or entry.android_url

    if not target:
        raise HTTPException(status_code=404, detail="No redirect URL configured")
    return RedirectResponse(url=target, status_code=302)


# ── Static QR API ─────────────────────────────────────────────────────────────

@app.post("/api/qr/static")
async def create_static(
    data: str = Form(...),
    fg_color: str = Form("#000000"),
    bg_color: str = Form("#FFFFFF"),
    dot_style: str = Form("square"),
    eye_style: str = Form("square"),
    container_shape: str = Form("square"),
    frame_text: str = Form(""),
    edge_line: str = Form("0"),
    edge_color: str = Form("#000000"),
    edge_width: int = Form(2),
    frame_color: str = Form("#000000"),
    frame_font: str = Form("arial"),
    container_effect: str = Form("flat"),
    logo: UploadFile = File(None),
):
    if not data.strip():
        raise HTTPException(status_code=400, detail="Data cannot be empty")
    logo_bytes = await logo.read() if logo and logo.filename else None
    img = build_qr_image(data.strip(), fg_color, bg_color, logo_bytes, dot_style, eye_style, container_shape, frame_text, edge_line == "1", edge_color, edge_width, frame_color, frame_font, container_effect)
    return {"qr_image": f"data:image/png;base64,{base64.b64encode(img).decode()}"}


# ── Dynamic QR API ────────────────────────────────────────────────────────────

@app.post("/api/qr/dynamic")
async def create_dynamic(
    destination_url: str = Form(...),
    fg_color: str = Form("#000000"),
    bg_color: str = Form("#FFFFFF"),
    dot_style: str = Form("square"),
    eye_style: str = Form("square"),
    container_shape: str = Form("square"),
    frame_text: str = Form(""),
    edge_line: str = Form("0"),
    edge_color: str = Form("#000000"),
    edge_width: int = Form(2),
    frame_color: str = Form("#000000"),
    frame_font: str = Form("arial"),
    container_effect: str = Form("flat"),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    if not destination_url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    code = _short_code()
    token = secrets.token_urlsafe(32)
    db.add(DynamicQR(
        short_code=code, destination_url=destination_url.strip(),
        edit_token=token, scan_count=0, created_at=datetime.utcnow(),
    ))
    db.commit()

    redirect_url = f"{BASE_URL}/r/{code}"
    logo_bytes = await logo.read() if logo and logo.filename else None
    img = build_qr_image(redirect_url, fg_color, bg_color, logo_bytes, dot_style, eye_style, container_shape, frame_text, edge_line == "1", edge_color, edge_width, frame_color, frame_font, container_effect)

    return {
        "short_code": code,
        "redirect_url": redirect_url,
        "manage_url": f"{BASE_URL}/manage/{code}?token={token}",
        "qr_image": f"data:image/png;base64,{base64.b64encode(img).decode()}",
    }


@app.post("/api/qr/dynamic/{short_code}/update")
async def update_dynamic(
    short_code: str,
    destination_url: str = Form(...),
    token: str = Form(...),
    db: Session = Depends(get_db),
):
    entry = db.query(DynamicQR).filter(DynamicQR.short_code == short_code).first()
    if not entry or entry.edit_token != token:
        raise HTTPException(status_code=403, detail="Invalid token")
    entry.destination_url = destination_url.strip()
    db.commit()
    return {"success": True, "destination_url": entry.destination_url}


@app.get("/api/qr/dynamic/{short_code}/download")
async def download_dynamic(short_code: str, token: str, db: Session = Depends(get_db)):
    entry = db.query(DynamicQR).filter(DynamicQR.short_code == short_code).first()
    if not entry or entry.edit_token != token:
        raise HTTPException(status_code=403, detail="Invalid token")
    img = build_qr_image(f"{BASE_URL}/r/{short_code}")
    return StreamingResponse(
        io.BytesIO(img), media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=qr-{short_code}.png"},
    )


# ── App Store QR API ──────────────────────────────────────────────────────────

@app.post("/api/qr/app")
async def create_app_qr(
    ios_url: str = Form(""),
    android_url: str = Form(""),
    fallback_url: str = Form(""),
    fg_color: str = Form("#000000"),
    bg_color: str = Form("#FFFFFF"),
    dot_style: str = Form("square"),
    eye_style: str = Form("square"),
    container_shape: str = Form("square"),
    frame_text: str = Form(""),
    edge_line: str = Form("0"),
    edge_color: str = Form("#000000"),
    edge_width: int = Form(2),
    frame_color: str = Form("#000000"),
    frame_font: str = Form("arial"),
    container_effect: str = Form("flat"),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    if not ios_url.strip() and not android_url.strip():
        raise HTTPException(status_code=400, detail="Provide at least one store URL")

    code = _short_code()
    db.add(AppRedirect(
        short_code=code,
        ios_url=ios_url.strip() or None,
        android_url=android_url.strip() or None,
        fallback_url=fallback_url.strip() or None,
        scan_count=0,
        created_at=datetime.utcnow(),
    ))
    db.commit()

    redirect_url = f"{BASE_URL}/app/{code}"
    logo_bytes = await logo.read() if logo and logo.filename else None
    img = build_qr_image(redirect_url, fg_color, bg_color, logo_bytes, dot_style, eye_style, container_shape, frame_text, edge_line == "1", edge_color, edge_width, frame_color, frame_font, container_effect)

    return {
        "short_code": code,
        "redirect_url": redirect_url,
        "qr_image": f"data:image/png;base64,{base64.b64encode(img).decode()}",
    }
