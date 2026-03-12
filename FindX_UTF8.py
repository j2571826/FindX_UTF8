import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import os
import fnmatch

stop_event = threading.Event()

def browse_folder():
    """開啟資料夾選擇對話框"""
    folder = filedialog.askdirectory()
    if folder:
        normalized_path = os.path.normpath(folder)
        path_var.set(normalized_path)

def perform_search():
    """收集輸入資料並啟動搜尋執行緒"""
    keywords_text = text_keywords.get("1.0", tk.END).strip()
    keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
    folder_path = path_var.get().strip()
    file_patterns_text = pattern_var.get().strip().replace(';', ',')
    file_patterns = [p.strip() for p in file_patterns_text.split(',') if p.strip()]

    if not keywords:
        messagebox.showwarning("警告", "請至少輸入一個關鍵字！")
        return
    if not folder_path or not os.path.exists(folder_path):
        messagebox.showwarning("警告", "請選擇有效的資料夾路徑！")
        return
    if not file_patterns:
        file_patterns = ['*']

    is_subfolder = subfolder_var.get()
    is_case_sensitive = case_var.get()
    is_compact = compact_var.get() # 取得是否為精簡模式(僅顯示檔名)

    stop_event.clear()

    btn_search.config(state=tk.DISABLED, text="⏳ 搜尋中...", bg="#ff9800")
    btn_export.config(state=tk.DISABLED)
    btn_stop.config(state=tk.NORMAL, bg="#f44336") 
    
    text_output.delete("1.0", tk.END)
    text_output.insert(tk.END, f"🚀 開始搜尋資料夾: {folder_path}\n")
    text_output.insert(tk.END, "請稍候...\n")

    thread = threading.Thread(target=search_logic, args=(keywords, folder_path, file_patterns, is_subfolder, is_case_sensitive, is_compact))
    thread.daemon = True
    thread.start()

def stop_search():
    """觸發停止旗標"""
    stop_event.set()
    btn_stop.config(state=tk.DISABLED, text="🛑 停止中...")

def search_logic(keywords, folder_path, file_patterns, is_subfolder, is_case_sensitive, is_compact):
    """實際的搜尋邏輯 (依關鍵字分組)"""
    total_result_count = 0
    is_aborted = False
    
    # 根據模式動態調整單位的文字
    unit_text = "個符合的檔案" if is_compact else "筆符合的行數"
    
    try:
        # 第一步：先收集所有符合條件的檔案路徑
        target_files = []
        for root, dirs, files in os.walk(folder_path):
            if stop_event.is_set():
                is_aborted = True
                break
            
            if not is_subfolder:
                dirs.clear()

            for file in files:
                if any(fnmatch.fnmatch(file, p) for p in file_patterns):
                    target_files.append(os.path.join(root, file))

        # 第二步：依據每個關鍵字分別去掃描這些檔案
        if not is_aborted:
            for kw in keywords:
                if stop_event.is_set():
                    is_aborted = True
                    break

                search_kw = kw if is_case_sensitive else kw.lower()
                kw_result_count = 0
                
                text_output.insert(tk.END, f"\n{'='*20} 關鍵字: {kw} {'='*20}\n")
                text_output.see(tk.END)

                for filepath in target_files:
                    if stop_event.is_set():
                        is_aborted = True
                        break

                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if stop_event.is_set():
                                    is_aborted = True
                                    break
                                
                                clean_line = line.replace('\x00', '').strip()
                                if not clean_line:
                                    continue

                                check_line = clean_line if is_case_sensitive else clean_line.lower()
                                
                                # 只要在這行找到關鍵字
                                if search_kw in check_line:
                                    if is_compact:
                                        # 【精簡模式】：只印檔名，而且立刻中斷這個檔案的讀取 (加速！)
                                        text_output.insert(tk.END, f"{filepath}\n")
                                        kw_result_count += 1
                                        total_result_count += 1
                                        text_output.see(tk.END)
                                        break # 跳出 for line in f 的迴圈，直接換下一個檔案
                                    else:
                                        # 【一般模式】：印出檔名與內容，並繼續尋找同一檔案的下一行
                                        result_line = f"{filepath} : {clean_line}\n"
                                        text_output.insert(tk.END, result_line)
                                        kw_result_count += 1
                                        total_result_count += 1
                                        if kw_result_count % 10 == 0:
                                            text_output.see(tk.END)
                    except Exception:
                        pass
                
                text_output.insert(tk.END, f"👉 [{kw}] 共找到 {kw_result_count} {unit_text}。\n")
                text_output.see(tk.END)

        if is_aborted:
            text_output.insert(tk.END, f"\n⚠️ 搜尋已手動中斷！總計找到 {total_result_count} {unit_text}。")
        else:
            text_output.insert(tk.END, f"\n✅ 搜尋完成！總計找到 {total_result_count} {unit_text}。")
        
        text_output.see(tk.END)
        
    except Exception as e:
        text_output.insert(tk.END, f"\n❌ 發生錯誤: {str(e)}")
        text_output.see(tk.END)
    finally:
        btn_search.config(state=tk.NORMAL, text="🔍 開始搜尋", bg="#4CAF50")
        btn_stop.config(state=tk.DISABLED, text="⏹️ 停止搜尋", bg="#cccccc") 
        btn_export.config(state=tk.NORMAL)

def export_results():
    """將畫面上的文字匯出成 txt 檔案"""
    content = text_output.get("1.0", tk.END).strip()
    if not content:
        messagebox.showinfo("提示", "目前沒有內容可以匯出喔！")
        return
    
    filepath = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        title="匯出搜尋結果",
        initialfile="FindX_Output.txt"
    )
    
    if filepath:
        normalized_filepath = os.path.normpath(filepath)
        try:
            with open(normalized_filepath, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            messagebox.showinfo("成功", f"結果已成功匯出至:\n{normalized_filepath}")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出失敗:\n{str(e)}")

def select_all(event):
    """修復 Tkinter 的 Ctrl+A 全選功能"""
    text_output.tag_add(tk.SEL, "1.0", tk.END)
    text_output.mark_set(tk.INSERT, "1.0")
    text_output.see(tk.INSERT)
    return 'break'

# === GUI 介面設計 ===
root = tk.Tk()
root.title("FindX_UTF8 搜尋工具")
root.geometry("750x620") 
root.configure(padx=15, pady=15)

# 1. 關鍵字輸入區
tk.Label(root, text="輸入關鍵字 (每行一個):", font=("微軟正黑體", 12, "bold")).pack(anchor=tk.W)
text_keywords = scrolledtext.ScrolledText(root, height=5, font=("微軟正黑體", 10))
text_keywords.pack(fill=tk.X, pady=(0, 10))

# 2. 目標資料夾設定區
frame_path = tk.Frame(root)
frame_path.pack(fill=tk.X, pady=(0, 10))
tk.Label(frame_path, text="搜尋資料夾:", font=("微軟正黑體", 12, "bold")).pack(side=tk.LEFT)
path_var = tk.StringVar()
tk.Entry(frame_path, textvariable=path_var, font=("微軟正黑體", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
tk.Button(frame_path, text="瀏覽...", command=browse_folder, font=("微軟正黑體", 9)).pack(side=tk.LEFT)

# 3. 檔案類型設定區
frame_pattern = tk.Frame(root)
frame_pattern.pack(fill=tk.X, pady=(0, 10))
tk.Label(frame_pattern, text="目標檔案名稱 (逗號分隔):", font=("微軟正黑體", 12, "bold")).pack(side=tk.LEFT)
pattern_var = tk.StringVar(value="*.fmb, *.rdf, *.txt, *.sql")
tk.Entry(frame_pattern, textvariable=pattern_var, font=("微軟正黑體", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

# 4. 進階選項區 (新增：僅顯示檔名)
frame_options = tk.Frame(root)
frame_options.pack(fill=tk.X, pady=(0, 10))
subfolder_var = tk.BooleanVar(value=True) 
case_var = tk.BooleanVar(value=False)
compact_var = tk.BooleanVar(value=False) # 預設不勾選，維持原本詳細輸出
tk.Checkbutton(frame_options, text="包含子資料夾", variable=subfolder_var, font=("微軟正黑體", 10)).pack(side=tk.LEFT, padx=(0, 15))
tk.Checkbutton(frame_options, text="區分大小寫", variable=case_var, font=("微軟正黑體", 10)).pack(side=tk.LEFT, padx=(0, 15))
tk.Checkbutton(frame_options, text="僅顯示檔名 (加快速度)", variable=compact_var, font=("微軟正黑體", 10, "bold"), fg="#1976D2").pack(side=tk.LEFT)

# 5. 按鈕區 (三顆按鈕並排)
frame_buttons = tk.Frame(root)
frame_buttons.pack(fill=tk.X, pady=(5, 10))
btn_search = tk.Button(frame_buttons, text="🔍 開始搜尋", command=perform_search, font=("微軟正黑體", 11, "bold"), bg="#4CAF50", fg="white", pady=5)
btn_search.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

btn_stop = tk.Button(frame_buttons, text="⏹️ 停止搜尋", command=stop_search, state=tk.DISABLED, font=("微軟正黑體", 11, "bold"), bg="#cccccc", fg="white", pady=5)
btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

btn_export = tk.Button(frame_buttons, text="💾 匯出結果", command=export_results, font=("微軟正黑體", 11, "bold"), bg="#008CBA", fg="white", pady=5)
btn_export.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 0))

# 6. 輸出結果區
tk.Label(root, text="搜尋結果:", font=("微軟正黑體", 12, "bold")).pack(anchor=tk.W)
text_output = scrolledtext.ScrolledText(root, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
text_output.pack(fill=tk.BOTH, expand=True)

# 綁定 Ctrl+A 全選修正
text_output.bind("<Control-a>", select_all)
text_output.bind("<Control-A>", select_all)

# 啟動主迴圈
root.mainloop()