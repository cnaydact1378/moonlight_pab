[달빛 팹 관리실 v0.2]

가장 쉬운 배포 방법

1. 이 ZIP의 압축을 풉니다.
2. 압축을 푼 폴더 안의 파일을 모두 GitHub 저장소 최상단에 올립니다.
3. GitHub에서 Commit changes를 누릅니다.
4. Streamlit Cloud에서 Main file path를 "대시보드.py"로 지정합니다.
5. Deploy 또는 Reboot app을 누릅니다.

정상 파일 구조

moonlight_pab/
├─ 대시보드.py
├─ requirements.txt
├─ 달빛팹_검사기록.csv
└─ README_먼저읽기.txt

CSV는 이미 포함되어 있으므로 별도로 이름을 바꿀 필요가 없습니다.
앱 실행 후 왼쪽의 "새 CSV 불러오기"를 사용하면 다른 CSV도 바로 분석할 수 있습니다.

내 컴퓨터에서 실행할 때

pip install -r requirements.txt
streamlit run 대시보드.py
