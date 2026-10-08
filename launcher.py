import sys
import traceback
from pathlib import Path


if __name__ == '__main__':
    try:
        from lab_apps.scripts.pointlock.camera_viewer import main
        main()
    except SystemExit:
        raise
    except Exception:
        if '--smoke-report' in sys.argv:
            index = sys.argv.index('--smoke-report') + 1
            if index < len(sys.argv):
                report = Path(sys.argv[index])
                report.write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
        raise
