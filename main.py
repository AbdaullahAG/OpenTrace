import webview
import os
import time

class BackendAPI:
    def handle_file_upload(self, file_path):
        """
        Validates the existence of the provided file path.
        Called by the frontend during the file selection sequence.
        """
        print(f"File received in Python: {file_path}")
        if os.path.exists(file_path):
            return {"status": "success", "message": "File linked successfully"}
        return {"status": "error", "message": "File not found"}

    def trigger_analysis(self):
        """
        Initiates the algorithmic analysis pipeline.
        Currently implements a placeholder delay to test UI asynchronous state management.
        """
        print("Analysis pipeline triggered by frontend.")
        
        time.sleep(3)
        
        return {
            "success": True,
            "message": "<h3>Analysis Complete</h3><p>Local analysis bridge connected successfully.</p>"
        }

def start():
    print("Starting OpenTrace GUI...")
    api = BackendAPI()
    
    # تحديد مسار ملف الواجهة المطلق لتجنب أخطاء المسارات
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'app', 'gui', 'index.html')
    
    print(f"Loading UI from: {html_path}")
    
    # إنشاء نافذة التطبيق
    webview.create_window(
        title='OpenTrace',
        url=f'file://{html_path}',
        js_api=api,
        width=1200,
        height=800
    )
    
    # نقطة التشغيل الإلزامية لإبقاء النافذة مفتوحة
    webview.start(debug=True)

if __name__ == '__main__':
    start()