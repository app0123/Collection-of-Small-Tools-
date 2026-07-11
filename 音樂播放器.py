import os
import sys
import subprocess
import time
import random
import tempfile

# 啟用 Windows CMD 的 ANSI 控制碼支援 (用於無閃爍的游標定位)
if os.name == 'nt':
    os.system('')

# 徹底隱藏 Pygame 的歡迎訊息
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# ==================== 1. 自動依賴套件檢測與安裝 ====================
REQUIRED_PACKAGES = ["pygame", "mutagen"]
FFMPEG_PACKAGE = "imageio-ffmpeg"

def check_and_install_dependencies():
    missing_packages = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing_packages.append(pkg)
    
    if missing_packages:
        print("=" * 65)
        print(f"【系統提示】需安裝基礎核心套件: {', '.join(missing_packages)}")
        choice = input("是否同意自動透過 pip 下載並安裝？(Y/N): ").strip().lower()
        if choice == 'y':
            for pkg in missing_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            print("基礎套件安裝完成！\n")
            time.sleep(1)
        else:
            sys.exit(1)

check_and_install_dependencies()
import pygame
from mutagen import File as MutagenFile

try:
    import msvcrt
except ImportError:
    print("本程式的快捷鍵功能目前專為 Windows CMD 設計。")
    sys.exit(1)

# ==================== 1.5 FFmpeg 擴充檢測 ====================
HAS_FFMPEG = False
FFMPEG_EXE_PATH = None

def setup_ffmpeg():
    global HAS_FFMPEG, FFMPEG_EXE_PATH
    try:
        import imageio_ffmpeg
        FFMPEG_EXE_PATH = imageio_ffmpeg.get_ffmpeg_exe()
        HAS_FFMPEG = True
    except ImportError:
        print("=" * 65)
        print("【進階格式支援提示】")
        print("若要支援 .webm, .m4a 等格式，需下載 FFmpeg 解碼核心。")
        print(" - 下載後永久支援離線解碼，不需連網。")
        print("=" * 65)
        choice = input("是否同意自動下載 FFmpeg 核心套件？(若選 N 則僅支援 MP3/WAV/FLAC) (Y/N): ").strip().lower()
        
        if choice == 'y':
            print("\n正在下載 FFmpeg 核心，檔案較大，請耐心稍候...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", FFMPEG_PACKAGE])
                import imageio_ffmpeg
                FFMPEG_EXE_PATH = imageio_ffmpeg.get_ffmpeg_exe()
                HAS_FFMPEG = True
                print(" ➔ FFmpeg 核心安裝成功！")
                time.sleep(2)
            except Exception as e:
                print(f" ➔ 安裝失敗: {e}")
                time.sleep(2)

setup_ffmpeg()

# ==================== 2. 功能邏輯與核心設定 ====================
NATIVE_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.flac', '.opus')
EXTENDED_EXTENSIONS = ('.webm', '.m4a', '.aac', '.ape', '.wv', '.alac', '.mp4')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_audio_length(path):
    """獲取音訊長度 (加入雙重保險機制)"""
    try:
        # 第一層：嘗試用 mutagen 讀取標籤
        length = MutagenFile(path).info.length
        if length > 0:
            return length
    except:
        pass
        
    try:
        # 第二層：如果是轉檔出來的純 wav，直接請 pygame 暴力解析長度
        return pygame.mixer.Sound(path).get_length()
    except:
        return 0

def convert_to_temp_wav(source_path):
    temp_dir = tempfile.gettempdir()
    for f in os.listdir(temp_dir):
        if f.startswith("pygame_temp_") and f.endswith(".wav"):
            try: os.remove(os.path.join(temp_dir, f))
            except: pass
            
    temp_wav = os.path.join(temp_dir, f"pygame_temp_{random.randint(10000, 99999)}.wav")
    subprocess.run(
        [FFMPEG_EXE_PATH, '-y', '-i', source_path, temp_wav],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return temp_wav

def draw_player_ui(song_name, current_sec, total_sec, status, mode, show_help=False):
    sys.stdout.write("\033[H")
    
    ui = f"{'=' * 65}\n"
    ui += "        CMD Terminal Pure-Audio Player v2.4\n"
    ui += f"  [ 狀態 ] {status:<15} | [ 模式 ] {mode}\n"
    ui += f"{'=' * 65}\n"
    # 稍微加寬顯示長度，讓長歌名可以多顯示一點
    ui += f" ▶ 目前播放: {song_name[:55]:<55}\n\n"
    
    bar_length = 30
    progress = current_sec / total_sec if total_sec > 0 else 0
    filled = int(bar_length * progress)
    bar = "=" * filled + ">" + " " * (bar_length - filled - 1)
    
    curr_str = f"{int(current_sec // 60):02d}:{int(current_sec % 60):02d}"
    tot_str = f"{int(total_sec // 60):02d}:{int(total_sec % 60):02d}"
    
    ui += f" [{bar}] {curr_str} / {tot_str}\n"
    ui += f"{'-' * 65}\n"
    
    if show_help:
        ui += " [ 快捷鍵總覽 ]\n"
        ui += " [空白鍵/P] 暫停與繼續  [N] 下一首      [B] 上一首\n"
        ui += " [→] 快進 5 秒          [←] 快退 5 秒   [S] 停止並返回\n"
        ui += " [R] 切換播放模式       [H] 關閉幫助\n"
    else:
        ui += " [空白]暫停  [N]下一首  [B]上一首  [S]停止  [H]幫助\n"
        ui += " " * 65 + "\n" 
        ui += " " * 65 + "\n"
        
    ui += f"{'=' * 65}\n"
    
    sys.stdout.write(ui)
    sys.stdout.write("\033[J") 
    sys.stdout.flush()

def parse_audio_path(user_input):
    clean_path = user_input.strip(' "\'')
    valid_files = []
    if not clean_path: return []
    supported_exts = NATIVE_EXTENSIONS + EXTENDED_EXTENSIONS if HAS_FFMPEG else NATIVE_EXTENSIONS

    def check_file(p):
        if os.path.splitext(p)[1].lower() in supported_exts:
            valid_files.append(p)

    if os.path.isfile(clean_path):
        check_file(clean_path)
    elif os.path.isdir(clean_path):
        for file in os.listdir(clean_path):
            check_file(os.path.join(clean_path, file))
        valid_files.sort()

    return valid_files

# ==================== 3. 升級版播放迴圈 ====================
def play_audio_loop(playlist, initial_mode):
    pygame.mixer.init()

    # 💡 洗牌邏輯：隨機播放時，直接打亂真實清單
    if initial_mode == '隨機播放':
        random.shuffle(playlist) 

    modes = ['單次播放', '單曲循環', '歌單順序', '歌單循環', '隨機播放']
    current_mode_idx = modes.index(initial_mode) if initial_mode in modes else 0
    current_song_idx = 0
    
    while current_song_idx < len(playlist):
        song_path = playlist[current_song_idx]
        song_name = os.path.basename(song_path)
        
        ext = os.path.splitext(song_path)[1].lower()
        load_path = song_path
        status_prefix = "播放中"
        
        if ext not in NATIVE_EXTENSIONS and HAS_FFMPEG:
            clear_screen()
            print(f"【FFmpeg 解碼中】正在載入 {song_name[:40]}... 請稍候")
            load_path = convert_to_temp_wav(song_path)
            status_prefix = "播放中 (FFmpeg)"
            
        # 💡 重點修正：在確定最終播放檔案(load_path)後，才讀取長度！
        total_length = get_audio_length(load_path)
        
        pygame.mixer.music.load(load_path)
        pygame.mixer.music.play()
        
        is_paused = False
        show_help = False
        start_time = time.time()
        time_offset = 0.0 
        
        force_next = False
        force_prev = False
        
        sys.stdout.write("\033[2J") 
        
        while pygame.mixer.music.get_busy() or is_paused:
            current_time = (time.time() - start_time) + time_offset if not is_paused else time_offset
            current_time = max(0, min(current_time, total_length))
            
            status_text = "暫停中" if is_paused else status_prefix
            draw_player_ui(song_name, current_time, total_length, status_text, modes[current_mode_idx], show_help)
            
            if msvcrt.kbhit():
                key = msvcrt.getch()
                
                if key == b'\xe0': 
                    arrow = msvcrt.getch()
                    if arrow == b'M': 
                        time_offset = current_time + 5.0
                        pygame.mixer.music.set_pos(time_offset)
                        start_time = time.time()
                    elif arrow == b'K': 
                        time_offset = max(0.0, current_time - 5.0)
                        pygame.mixer.music.set_pos(time_offset)
                        start_time = time.time()
                    continue

                key = key.lower()
                
                if key in [b' ', b'p']: 
                    is_paused = not is_paused
                    if is_paused:
                        time_offset = current_time
                        pygame.mixer.music.pause()
                    else:
                        start_time = time.time()
                        pygame.mixer.music.unpause()
                        
                elif key == b's': 
                    pygame.mixer.music.stop()
                    try: pygame.mixer.music.unload()
                    except: pass
                    return 
                    
                elif key == b'n': 
                    force_next = True
                    pygame.mixer.music.stop()
                    break 
                    
                elif key == b'b': 
                    force_prev = True
                    pygame.mixer.music.stop()
                    break
                    
                elif key == b'r': 
                    current_mode_idx = (current_mode_idx + 1) % len(modes)
                    
                elif key == b'h': 
                    show_help = not show_help

            time.sleep(0.1)
            
        try: pygame.mixer.music.unload()
        except: pass
            
        # 💡 換歌邏輯更新
        if force_next:
            current_song_idx += 1
        elif force_prev:
            current_song_idx -= 1
        elif modes[current_mode_idx] == '單曲循環':
            pass 
        elif modes[current_mode_idx] == '單次播放':
            break 
        else:
            # 包括隨機播放、歌單循環，現在通通順著往下走就好
            current_song_idx += 1
            
        if current_song_idx >= len(playlist):
            if modes[current_mode_idx] in ['歌單循環', '隨機播放']:
                # 若跑到最後一首又要循環，重新洗牌/歸零
                if modes[current_mode_idx] == '隨機播放':
                    random.shuffle(playlist)
                current_song_idx = 0
            else:
                break
        elif current_song_idx < 0:
            current_song_idx = len(playlist) - 1 if modes[current_mode_idx] in ['歌單循環', '隨機播放'] else 0

# ==================== 4. 主程式選單 ====================
def main_player_loop():
    while True:
        clear_screen()
        print("=" * 65)
        print("        CMD Terminal Pure-Audio Player v2.4")
        print("=" * 65)
        print("請提供音訊檔案的『完整路徑』或『資料夾路徑』。")
        print("提示：你可以直接把音樂檔案或整包資料夾「拖曳」進這個視窗。")
        path_input = input("➔ 路徑 (或輸入 exit 離開): ").strip()
        
        if path_input.lower() == 'exit':
            print("\n感謝使用！音訊模組安全關閉。")
            break
            
        playlist = parse_audio_path(path_input)

        if not playlist:
            print("\n【提示】找不到可播放的音訊檔案！")
            input("按 Enter 鍵重新輸入...")
            continue
            
        clear_screen()
        print("=" * 65)
        print(f"  已載入 {len(playlist)} 首歌曲")
        print("=" * 65)
        
        mode_choice = None
        if len(playlist) == 1:
            print(" 1. 單次播放")
            print(" 2. 單曲循環")
            while mode_choice not in ['1', '2']:
                mode_choice = input("請選擇模式 (1-2): ").strip()
            
            mode_map = {'1': '單次播放', '2': '單曲循環'}
            play_audio_loop(playlist, mode_map[mode_choice])
            
        else:
            print(" 1. 歌單單次播放 (依序播完即停止)")
            print(" 2. 歌單全循環   (播完後從頭循環)")
            print(" 3. 隨機播放     (打亂順序輪播)")
            while mode_choice not in ['1', '2', '3']:
                mode_choice = input("請選擇模式 (1-3): ").strip()
                
            mode_map = {'1': '歌單順序', '2': '歌單循環', '3': '隨機播放'}
            play_audio_loop(playlist, mode_map[mode_choice])
            
        print("\n【播放結束】返回主選單...")
        time.sleep(1)

if __name__ == "__main__":
    try:
        main_player_loop()
    except KeyboardInterrupt:
        pygame.mixer.music.stop()
        print("\n程式已被使用者強制關閉。再見！")
        sys.exit(0)
