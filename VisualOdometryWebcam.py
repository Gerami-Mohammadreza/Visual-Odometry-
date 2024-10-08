import cv2
import numpy as np

# باز کردن وب‌کم
cap = cv2.VideoCapture(0)

# پارامترهای Lucas-Kanade optical flow
lk_params = dict(winSize=(21, 21), maxLevel=3,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))

# پارامترهای تشخیص ویژگی Shi-Tomasi corner
feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)

# خواندن اولین فریم و تبدیل به grayscale
ret, old_frame = cap.read()
if not ret:
    print("خطا در دسترسی به وب‌کم")
    exit()

old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)

# یافتن ویژگی‌های اولیه برای ردیابی
p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

# ایجاد ماسک برای کشیدن خطوط و ایجاد مپ
mask = np.zeros_like(old_frame)
map_image = np.zeros((600, 600, 3), dtype=np.uint8)  # نقشه ساده برای نمایش مسیر دوربین
trajectory_color = (255, 0, 0)  # رنگ مسیر در نقشه

# متغیرهای اولیه برای ذخیره مکان دوربین
cur_pos = np.array([300, 300], dtype=np.float32)  # شروع مکان در وسط تصویر نقشه
scale = 0.1  # مقیاس حرکت دوربین در نقشه

# متغیرهای چرخش و جابجایی
prev_angle = 0
prev_t = np.zeros((2, 1))

while True:
    ret, frame = cap.read()
    if not ret:
        print("خطا در دریافت فریم از وب‌کم")
        break

    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # محاسبه optical flow
    p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)

    if p1 is None:
        print("هیچ ویژگی جدیدی برای ردیابی پیدا نشد")
        break

    # انتخاب نقاطی که به خوبی دنبال شده‌اند
    good_new = p1[st == 1]
    good_old = p0[st == 1]

    # رسم خطوط و نقاط در ویدئو
    for i, (new, old) in enumerate(zip(good_new, good_old)):
        a, b = new.ravel()
        c, d = old.ravel()

        a, b, c, d = int(a), int(b), int(c), int(d)

        mask = cv2.line(mask, (a, b), (c, d), (0, 255, 0), 2)
        frame = cv2.circle(frame, (a, b), 5, (0, 0, 255), -1)

    img = cv2.add(frame, mask)

    # محاسبه ماتریس تغییرات
    E, mask_E = cv2.findEssentialMat(good_new, good_old, focal=1.0, pp=(0, 0), method=cv2.RANSAC, prob=0.999, threshold=1.0)
    _, R, t, mask_pose = cv2.recoverPose(E, good_new, good_old)

    # تخمین مکان دوربین با استفاده از اطلاعات ترجمه
    angle = np.arctan2(t[1], t[0])  # محاسبه زاویه حرکت
    translation = t[:2]  # تنها دو مقدار X و Y را استفاده می‌کنیم

    # به‌روزرسانی مکان دوربین
    cur_pos += translation.flatten() * scale

    # رسم مسیر در نقشه
    map_image = cv2.circle(map_image, (int(cur_pos[0]), int(cur_pos[1])), 2, trajectory_color, -1)

    # نمایش ویدئو و نقشه
    cv2.imshow('Visual Odometry', img)
    cv2.imshow('Map', map_image)

    # به روزرسانی فریم و نقاط قبلی
    old_gray = frame_gray.copy()
    p0 = good_new.reshape(-1, 1, 2)

    # خروج با فشار دادن کلید 'q'
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
