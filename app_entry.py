"""冻结打包入口；发行程序使用随附运行库，不依赖系统 Python。"""
import os
from pathlib import Path
import sys
import traceback

os.environ.setdefault("QT_API", "pyside6")


def main():
    if "--smoke-test" in sys.argv:
        from gaussian_lab.release_smoke import run
        index = sys.argv.index("--smoke-test")
        if index + 1 >= len(sys.argv):
            raise ValueError("--smoke-test 必须指定输出目录")
        return run(Path(sys.argv[index + 1]))
    from gaussian_lab.gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # 窗口程序没有控制台，将启动诊断保存在用户日志目录中。
        log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GaussianLab" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log = log_dir / "startup-error.txt"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication([])
            QMessageBox.critical(None, "GaussianLab 启动失败", f"请将错误记录反馈给开发者：\n{log}")
        finally:
            sys.exit(1)
