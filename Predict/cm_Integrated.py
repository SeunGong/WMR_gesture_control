import os
import cv2
import shutil
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from ultralytics import YOLO
from sklearn.metrics import confusion_matrix

gesture = None
count_print = 0

def calculate_angle_arm(a, b, c):

    # 각 값을 받아 넘파이 배열로 변형
    a = np.array(a)  # 첫번째
    b = np.array(b)  # 두번째
    c = np.array(c)  # 세번째

    # 라디안을 계산하고 실제 각도로 변경한다.
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - \
        np.arctan2(a[1]-b[1], a[0]-b[0])
    angle_arm = np.abs(radians*180.0/np.pi)

    # 180도가 넘으면 360에서 뺀 값을 계산한다.
    if angle_arm > 180.0:
        angle_arm = 360-angle_arm

    # 각도를 리턴한다.
    return angle_arm

# YOLOv8 모델을 로드합니다.
model_pose = YOLO("yolov8m-pose")
model_hands = YOLO("240503.pt")

source_folder = r"C:\Users\eofeh\Desktop\Model\datasets\valid\images"
folder_path  = r"C:\Users\eofeh\Desktop\Model\datasets\valid\labels"

predict_folder = os.path.join(source_folder, '../Predicted')
mismatch_folder = os.path.join(source_folder, '../Mismatch_image')  # 불일치 이미지를 저장할 폴더

# 폴더 생성을 위한 함수
def create_folder(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder created: {folder_path}")
        else:
            print(f"Folder already exists: {folder_path}")
    except Exception as e:
        print(f"Failed to create folder {folder_path}. Error: {str(e)}")

create_folder(predict_folder)
create_folder(mismatch_folder)

# 지원하는 이미지 확장자 목록
image_extensions = ['.jpg', '.png', '.jpeg']  # 이미지 파일 확장자

labels=[]
gestures=[]
file_names=[]

for filename in os.listdir(folder_path):
    # 파일 확장자가 .txt인 경우
    if filename.endswith('.txt'):
        # 파일 전체 경로 구성
        file_path = os.path.join(folder_path, filename)
        
        # 파일 열기
        with open(file_path, 'r') as file:
            # 파일에서 첫 번째 줄 읽기
            first_line = file.readline().strip()
            
            # 첫 번째 줄의 첫 번째 값 저장 (공백으로 구분된 경우)
            label = first_line.split()[0]
            labels.append(int(label))
            
for subdir, dirs, files in os.walk(source_folder):
    # 현재 순회 중인 폴더가 target_folder면 건너뛰기
    if subdir.startswith(predict_folder):
        continue

    for file in files:
        # 파일 확장자가 이미지 확장자 목록에 있는지 확인
            
        if any(file.lower().endswith(ext) for ext in image_extensions):
            # 이미지 파일의 원본 경로
            source_path = os.path.join(subdir, file)
            # 이미지 파일의 새 경로 (대상 폴더)
            target_path = os.path.join(predict_folder, file)

            # 파일명 충돌 방지
            if os.path.exists(target_path):
                base, extension = os.path.splitext(file)
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(
                        predict_folder, f"{base}_{counter}{extension}")
                    counter += 1

            image = cv2.imread(source_path)
            color_image = np.asanyarray(image)
            
            #predict----------------------------------------------------------
            angle_arm = 0
            count_gesture=0

            box_cx, box_cy = None, None  # predict box
            box_pose_cx, box_pose_cy = None, None  # predict box
            
            # results_hands = model_hands(color_image, conf=0.8, verbose=False)  # Predict hands
            results_hands = model_hands(color_image, verbose=False)  # Predict hands
            
            hands = 'N'
            
            if results_hands is not None:
                for r in results_hands:
                    boxes = r.boxes
                    for box in boxes:
                        
                        b = box.xyxy[0].to('cpu').detach().numpy().copy()
                        c = box.cls
                        x1, y1, x2, y2 = map(int, b[:4])
                        box_cx, box_cy = int(
                            (x2 - x1) / 2 + x1), int((y2 - y1) / 2 + y1)
                        # hands = model_hands.names[int(c)]
                        # hands = int(c)
                        gesture = int(c)

                        # Drawing bounding box
                        cv2.rectangle(color_image, (x1, y1), (x2, y2),
                                        (0, 0, 255), thickness=2, lineType=cv2.LINE_4)
                        cv2.putText(color_image,  model_hands.names[int(c)], (x1, y1), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7, (0, 0, 255), 2, cv2.LINE_4)

            results_pose = model_pose(color_image, conf=0.8, verbose=False) # Predict coordinate_pose
            color_image = results_pose[0].plot()
            
            count_point = 6  # number of coordinate_pose
            
            distance_whl, distance_whr = None, None # Distance between winkle-hands

            coordinate_pose = np.zeros((count_point, 2))
            if results_pose is not None:
                for r in results_pose:
                    keypoints = r.keypoints
                    pose_boxes = r.boxes
                    if len(pose_boxes.xyxy) > 0:
                        b = pose_boxes.xyxy[0].to('cpu').detach().numpy().copy()
                        px1, py1, px2, py2 = map(int, b[:4])
                    
                    for i, k in enumerate(keypoints):
                        if k.xy[0].size(0) > 6:  # Ensure there are enough elements
                            coordinate_pose[0] = k.xy[0][6].cpu().numpy()
                            value_srx = int(coordinate_pose[0][0]) # Right shoulder
                            
                        if k.xy[0].size(0) > 8:  
                            coordinate_pose[1] = k.xy[0][8].cpu().numpy()  # Right elbow
                            
                        if k.xy[0].size(0) > 10:  
                            coordinate_pose[2] = k.xy[0][10].cpu().numpy() # Right wrist

                            if box_cx is not None:
                                distance_whr = np.sqrt((box_cx - int(coordinate_pose[2][0]))**2 + (box_cy - int(
                                    coordinate_pose[2][1]))**2)
                        if k.xy[0].size(0) > 5:
                            coordinate_pose[3] = k.xy[0][5].cpu().numpy()
                            value_slx = int(coordinate_pose[3][0]) # Left shoulder

                        if k.xy[0].size(0) > 7:
                            coordinate_pose[4] = k.xy[0][7].cpu().numpy() # Left elbow

                        if k.xy[0].size(0) > 9:
                            coordinate_pose[5] = k.xy[0][9].cpu().numpy() # Left wrist
                            
                            if box_cx is not None:
                                distance_whl = np.sqrt((box_cx - int(coordinate_pose[5][0]))**2 + (
                                    box_cy - int(coordinate_pose[5][1]))**2)

                    if distance_whl is not None and distance_whr is not None: #  Activate hand selection
                        if (distance_whl > distance_whr):
                            active_hands = 'RIGHT'
                            angle_arm = calculate_angle_arm(
                                coordinate_pose[0], coordinate_pose[1], coordinate_pose[2])
                        elif (distance_whl < distance_whr):
                            active_hands = 'LEFT'
                            angle_arm = calculate_angle_arm(
                                coordinate_pose[3], coordinate_pose[4], coordinate_pose[5])
                    
            """ condition           
            # conditions = {
            #     0: lambda angle_arm: angle_arm > 0 and angle_arm < 180,
            #     1: lambda angle_arm: angle_arm > 0 and angle_arm < 180,
            #     2: lambdazz angle_arm: angle_arm > 0 and angle_arm < 180,
            #     3: lambda angle_arm: angle_arm > 0 and angle_arm < 180,
            #     4: lambda angle_arm: angle_arm > 80 and angle_arm < 140, #next backwar and turn
            #     5: lambda angle_arm: angle_arm > 150 and angle_arm < 180,
            # }#0'STOP', 1'YOU', 2'TURN', 3'FORWARD', 4'BACKWARD', 5'POINTING'

            # if conditions.get(hands, lambda x: False)(angle_arm):
            #     gesture = hands
            # else:
            #     gesture = 6
    
             """
            if box_cx is not None and box_cy is not None:
                        if(box_cy<y1 or box_cy>y2 or box_cx<x1 or box_cx>x2):
                            gesture=6
            else:
                gesture=6
            gestures.append(gesture) #add predicted gesture to gestures array
            file_names.append(file)
            cv2.imwrite(target_path, color_image)
            #predict----------------------------------------------------------
                       
pred_labels = np.array(gestures)  # 모델과 post-processing을 통해 얻은 예측 결과
true_labels = np.array(labels)

with open('mismatch.txt', 'w') as file:
    for index, (pred_label, true_label) in enumerate(zip(pred_labels, true_labels)):
        if pred_label != true_label:
            file.write(f"{index}: {file_names[index]}: {pred_label} != {true_label}\n")

            # 불일치하는 이미지를 별도 폴더에 저장
            source_path = os.path.join(predict_folder, file_names[index])  # 이미지 파일 경로 재구성
            target_mismatch_path = os.path.join(mismatch_folder, f"mismatch_{file_names[index]}")
            shutil.copy(source_path, target_mismatch_path)

"""draw confusion matrix
cm = confusion_matrix(true_labels, pred_labels, labels=[0,3,4,2,5,1,6])

print(cm)
cm=np.transpose(cm)

# 각 열의 합으로 나누어 정규화
T_1_normalized_by_columns = cm / cm.sum(axis=0, keepdims=True)
T_1_normalized_by_columns = np.around(T_1_normalized_by_columns, decimals=2)
print("Normalized Confusion Matrix (by columns):")

# 출력 포맷을 대괄호로 묶고 소수점 두 자리까지 표시
for row in T_1_normalized_by_columns:
    formatted_row = "[" + ", ".join(format(x, ".2f") for x in row) + "]"
    print(formatted_row)

fig, ax = plt.subplots( figsize=(6,6) )
emotionlabels = ['Stop/Waving', 'Forward', 'Backward', 'Turn', 'Pointing','You','Background']
sns.heatmap(T_1_normalized_by_columns,
            cmap = 'Blues',
            annot = True,   # 실제 값을 표시한다
            linewidths=.5,  # 경계면 실선으로 구분하기
            vmin = 0,vmax = 1,
            xticklabels = emotionlabels,
            yticklabels = emotionlabels,
           )
plt.xlabel('True')
plt.ylabel('Predict')
plt.xticks(rotation=45, ha='right')  # Rotate labels and align them horizontally
plt.yticks(rotation=0)
ax.tick_params(axis='both', which='major', labelsize=12)  # Change label size
plt.tight_layout()
plt.savefig('cm(integrated).png', bbox_inches = 'tight', pad_inches=0)
plt.show()
"""