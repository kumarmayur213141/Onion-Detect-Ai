import base64
import io
import json
import os
from datetime import datetime

import cv2
import numpy as np

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="ONION DETECT",
    description="Automated Onion Quality Assessment & Grading Prototype",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "db.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def load_db():
    if not os.path.exists(DB_FILE):
        return {"batches": []}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"batches": []}


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "service": "ONION DETECT",
        "version": "1.0.0"
    }


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.get("/")
def home():
    return FileResponse(
        os.path.join(PUBLIC_DIR, "index.html")
    )


# ---------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------

def image_to_base64(image):
    success, buffer = cv2.imencode(
        ".jpg",
        image,
        [cv2.IMWRITE_JPEG_QUALITY, 88]
    )

    if not success:
        return None

    encoded = base64.b64encode(buffer).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded}"


# ---------------------------------------------------------
# ONION ANALYSIS
# ---------------------------------------------------------

def calculate_defect_score(crop):
    """
    Prototype defect estimator.

    Uses:
    - dark pixels
    - unusual saturation
    - brown/black regions

    This is NOT a trained disease classifier.
    """

    if crop is None or crop.size == 0:
        return 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    dark_pixels = np.mean(gray < 55)

    # Brown / reddish regions
    lower_brown = np.array([5, 50, 20])
    upper_brown = np.array([35, 255, 180])

    brown_mask = cv2.inRange(
        hsv,
        lower_brown,
        upper_brown
    )

    brown_ratio = np.mean(brown_mask > 0)

    score = (
        dark_pixels * 65
        + brown_ratio * 35
    )

    return round(float(np.clip(score, 0, 100)), 1)


def grade_from_values(size_mm, defect_score):
    """
    Prototype AGMARK-style demonstration logic.

    NOTE:
    These are configurable prototype rules,
    not a legal certification of AGMARK grade.
    """

    if defect_score >= 35:
        return "URS"

    if size_mm >= 45 and defect_score < 15:
        return "A"

    if size_mm >= 35 and defect_score < 25:
        return "B"

    if size_mm >= 30:
        return "B"

    return "URS"


def detect_onions(image):
    """
    Prototype computer vision pipeline.

    Uses:
    1. image normalization
    2. blur
    3. Hough circle detection
    4. contour fallback
    5. approximate size estimation
    6. defect estimation
    """

    original = image.copy()

    height, width = image.shape[:2]

    # Resize for faster processing
    max_dimension = 1100

    scale = 1.0

    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)

        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    display = image.copy()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Improve contrast
    gray = cv2.equalizeHist(gray)

    blurred = cv2.GaussianBlur(
        gray,
        (9, 9),
        2
    )

    detections = []

    # -----------------------------------------------------
    # METHOD 1: HOUGH CIRCLE
    # -----------------------------------------------------

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=35,
        param1=80,
        param2=30,
        minRadius=18,
        maxRadius=max(20, min(image.shape[:2]) // 4)
    )

    if circles is not None:

        circles = np.round(
            circles[0]
        ).astype(int)

        # Limit to reasonable number for prototype
        circles = circles[:60]

        for x, y, r in circles:

            x1 = max(0, x - r)
            y1 = max(0, y - r)

            x2 = min(image.shape[1], x + r)
            y2 = min(image.shape[0], y + r)

            crop = image[y1:y2, x1:x2]

            defect = calculate_defect_score(crop)

            # Approximate conversion.
            # Prototype calibration assumption.
            size_mm = round(
                max(20, min(100, r * 1.8)),
                1
            )

            grade = grade_from_values(
                size_mm,
                defect
            )

            detections.append({
                "x": int(x1),
                "y": int(y1),
                "width": int(x2 - x1),
                "height": int(y2 - y1),
                "size_mm": size_mm,
                "defect_score": defect,
                "grade": grade,
                "confidence": round(
                    max(70, 98 - defect * 0.25),
                    1
                )
            })

    # -----------------------------------------------------
    # METHOD 2: CONTOUR FALLBACK
    # -----------------------------------------------------

    if len(detections) < 3:

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Onion-like color range
        lower = np.array([0, 25, 25])
        upper = np.array([40, 255, 255])

        mask = cv2.inRange(
            hsv,
            lower,
            upper
        )

        kernel = np.ones(
            (7, 7),
            np.uint8
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []

        for contour in contours:

            area = cv2.contourArea(contour)

            if area < 800:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            if w < 30 or h < 30:
                continue

            aspect_ratio = w / max(h, 1)

            if aspect_ratio < 0.35 or aspect_ratio > 2.5:
                continue

            candidates.append(
                (area, x, y, w, h)
            )

        candidates.sort(
            reverse=True
        )

        for area, x, y, w, h in candidates[:50]:

            crop = image[
                y:y + h,
                x:x + w
            ]

            defect = calculate_defect_score(
                crop
            )

            diameter_px = (w + h) / 2

            size_mm = round(
                max(
                    20,
                    min(
                        100,
                        diameter_px * 0.55
                    )
                ),
                1
            )

            grade = grade_from_values(
                size_mm,
                defect
            )

            detections.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "size_mm": size_mm,
                "defect_score": defect,
                "grade": grade,
                "confidence": round(
                    max(65, 95 - defect * 0.3),
                    1
                )
            })

    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    filtered = []

    for item in detections:

        duplicate = False

        cx1 = item["x"] + item["width"] / 2
        cy1 = item["y"] + item["height"] / 2

        for old in filtered:

            cx2 = old["x"] + old["width"] / 2
            cy2 = old["y"] + old["height"] / 2

            distance = (
                (cx1 - cx2) ** 2
                + (cy1 - cy2) ** 2
            ) ** 0.5

            if distance < min(
                item["width"],
                item["height"]
            ) * 0.35:

                duplicate = True
                break

        if not duplicate:
            filtered.append(item)

    detections = filtered[:50]

    # -----------------------------------------------------
    # DRAW RESULTS
    # -----------------------------------------------------

    for index, item in enumerate(detections):

        x = item["x"]
        y = item["y"]
        w = item["width"]
        h = item["height"]

        grade = item["grade"]

        if grade == "A":
            color = (0, 180, 0)
        elif grade == "B":
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)

        cv2.rectangle(
            display,
            (x, y),
            (x + w, y + h),
            color,
            3
        )

        label = f"#{index + 1} {grade}"

        cv2.rectangle(
            display,
            (x, max(0, y - 28)),
            (x + 100, y),
            color,
            -1
        )

        cv2.putText(
            display,
            label,
            (x + 5, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2
        )

    # -----------------------------------------------------
    # RESULT SUMMARY
    # -----------------------------------------------------

    count_a = sum(
        1 for x in detections
        if x["grade"] == "A"
    )

    count_b = sum(
        1 for x in detections
        if x["grade"] == "B"
    )

    count_urs = sum(
        1 for x in detections
        if x["grade"] == "URS"
    )

    count = len(detections)

    if count == 0:

        batch_grade = "NO DETECTION"

    elif count_urs / count >= 0.25:

        batch_grade = "URS"

    elif count_a / count >= 0.60:

        batch_grade = "A"

    else:

        batch_grade = "B"

    avg_size = round(
        float(
            np.mean([
                x["size_mm"]
                for x in detections
            ])
        ),
        1
    ) if detections else 0

    avg_defect = round(
        float(
            np.mean([
                x["defect_score"]
                for x in detections
            ])
        ),
        1
    ) if detections else 0

    result = {
        "batch_grade": batch_grade,
        "onion_count": count,
        "grade_distribution": {
            "A": count_a,
            "B": count_b,
            "URS": count_urs
        },
        "average_size_mm": avg_size,
        "average_defect_score": avg_defect,
        "detections": detections,
        "annotated_image": image_to_base64(display),
        "processed_at": datetime.now().isoformat()
    }

    return result


# ---------------------------------------------------------
# ANALYZE API
# ---------------------------------------------------------

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):

    if not file.content_type:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid file"
            }
        )

    allowed = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]

    if file.content_type not in allowed:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Please upload JPG, PNG or WEBP image."
            }
        )

    contents = await file.read()

    if len(contents) > 15 * 1024 * 1024:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Image size must be below 15 MB."
            }
        )

    np_array = np.frombuffer(
        contents,
        np.uint8
    )

    image = cv2.imdecode(
        np_array,
        cv2.IMREAD_COLOR
    )

    if image is None:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Could not read image."
            }
        )

    result = detect_onions(image)

    # Save batch history
    db = load_db()

    batch_record = {
        "id": len(db["batches"]) + 1,
        "time": result["processed_at"],
        "onion_count": result["onion_count"],
        "batch_grade": result["batch_grade"],
        "grade_distribution": result["grade_distribution"],
        "average_size_mm": result["average_size_mm"],
        "average_defect_score": result["average_defect_score"]
    }

    db["batches"].append(batch_record)

    # Keep latest 100 records
    db["batches"] = db["batches"][-100:]

    save_db(db)

    return result


# ---------------------------------------------------------
# HISTORY API
# ---------------------------------------------------------

@app.get("/api/history")
def history():

    db = load_db()

    return {
        "batches": db.get("batches", [])
    }


# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------

app.mount(
    "/",
    StaticFiles(
        directory=PUBLIC_DIR,
        html=True
    ),
    name="public"
)