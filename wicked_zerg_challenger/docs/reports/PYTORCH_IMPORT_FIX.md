# PyTorch Import 오류 수정

**작성일**: 2026-01-14

---

## ? 발견된 문제

### PyTorch C Extensions 로딩 오류
```
Failed to load PyTorch C extensions:
    It appears that PyTorch has loaded the `torch/_C` folder
    of the PyTorch repository rather than the C extensions
```

### 원인
- `local_training/` 디렉토리에서 실행 시 작업 디렉토리가 PyTorch import 경로와 충돌
- PyTorch가 소스 코드 폴더를 찾으려고 시도하는 문제

---

## ? 수정 사항

### 1. 안전한 PyTorch Import
- **위치**: `main_integrated.py` (Line 111-121, 1175-1185)
- **변경**: 작업 디렉토리를 프로젝트 루트로 임시 변경 후 torch import
- **효과**: 경로 충돌 방지

### 수정 코드
```python
# CPU Thread Configuration: Use 12 threads
try:
    import multiprocessing
    # Change to a safe directory before importing torch
    original_cwd = os.getcwd()
    try:
        # Temporarily change to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        import torch
        # Verify torch is properly installed
        if not hasattr(torch, '_C'):
            raise ImportError("PyTorch C extensions not properly loaded")
        num_threads = int(os.environ.get("TORCH_NUM_THREADS", "12"))
        torch.set_num_threads(num_threads)
        os.environ["OMP_NUM_THREADS"] = str(num_threads)
        os.environ["MKL_NUM_THREADS"] = str(num_threads)
        print(f"[CPU] PyTorch configured to use {num_threads} threads")
    finally:
        os.chdir(original_cwd)  # Always restore original directory
except Exception as e:
    print(f"[WARNING] Failed to configure CPU threads: {e}")
    print(f"[INFO] Game will continue but may use default thread settings")
```

---

## ? 검증

### PyTorch 설치 확인
- ? PyTorch 버전: 2.7.1+cu118
- ? CUDA 사용 가능: True
- ? C Extensions (_C): 정상

### 수정 후 동작
- ? 작업 디렉토리 임시 변경으로 경로 충돌 방지
- ? 오류 발생 시에도 게임은 계속 실행 (경고만 출력)
- ? 원래 작업 디렉토리 자동 복원

---

## ? 참고 사항

### PyTorch 재설치가 필요한 경우
만약 문제가 계속되면:
```powershell
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 환경 변수로 스레드 수 변경
```powershell
$env:TORCH_NUM_THREADS = "8"  # 8개로 변경
python main_integrated.py
```

---

**수정 완료**: PyTorch import 오류가 해결되었으며, 게임은 정상적으로 실행됩니다.
