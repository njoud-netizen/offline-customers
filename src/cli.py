"""نقطة الدخول لسطر الأوامر: أمر واحد يقرأ الفواتير، يتصل بشيت المزروع، ويطلع الملفات الأربعة."""
import argparse
import sys

from .config import load_config
from .pipeline import run_pipeline
from .sheets import GoogleSheetsConnectionError


def main():
    parser = argparse.ArgumentParser(description="تحديد العملاء الأوفلاين — مطابقة فواتير المبيعات مع شيت المزروع")
    parser.add_argument("invoice_file", help="مسار ملف الفواتير (Excel أو CSV)")
    parser.add_argument("--config", default=None, help="مسار ملف config.yaml (اختياري)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    try:
        result = run_pipeline(args.invoice_file, cfg=cfg, on_progress=lambda msg: print(msg))
    except GoogleSheetsConnectionError as e:
        print(f"\n[خطأ] {e}")
        sys.exit(1)

    print("\n=== ملخص التشغيل ===")
    for k, v in result.summary.items():
        print(f"{k}: {v}")
    print("\n=== الملفات الناتجة ===")
    for k, v in result.output_paths.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
