import os
import random
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
# service_role 키가 있으면 그걸 사용하고, 없으면 anon 키 사용
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

def seed():
    print("Generating 5 models...")
    models_data = []
    names = ["Anna Smith", "Elena Petrova", "John Doe", "Liam Johnson", "Maria Garcia"]
    passports = ["Anna Smith", "Elena Petrova", "John Doe", "Liam Johnson", "Maria Garcia"]
    nationalities = ["US", "Russia", "UK", "Canada", "Spain"]
    genders = ["Female", "Female", "Male", "Male", "Female"]
    
    for i in range(5):
        m = {
            "model_name": names[i],
            "passport_name": passports[i],
            "date_of_birth": (date(1995, 1, 1) + timedelta(days=random.randint(0, 3000))).isoformat(),
            "nationality": nationalities[i],
            "gender": genders[i],
            "height": random.choice([170, 175, 180, 185, 172]),
            "bust": 32.0,
            "waist": 24.0,
            "hips": 34.0,
            "shoe_size": random.choice(["US 8", "US 9", "EU 40", "EU 42"]),
            "mother_agency": "Top Models",
            "guarantee_amount": random.choice([0, 1000, 2000]),
            "mac_rate": 20,
            "contract_start": (date.today() - timedelta(days=30)).isoformat(),
            "contract_end": (date.today() + timedelta(days=330)).isoformat(),
            "visa_status": "approved",
            "status": "active"
        }
        models_data.append(m)
        
    # 모델 저장
    res = supabase.table("models").insert(models_data).execute()
    inserted_models = res.data
    print(f"Inserted {len(inserted_models)} models.")
    
    print("Generating 30 schedules...")
    schedules_data = []
    clients = ["Vogue", "GQ", "Samsung", "Nike", "Adidas", "Hyundai", "Zara", "H&M"]
    
    for i in range(30):
        model = random.choice(inserted_models)
        # 오늘 기준으로 -15일 ~ +30일 사이의 스케줄
        sched_date = date.today() + timedelta(days=random.randint(-15, 30))
        
        # 시간 설정 (오전 7시 ~ 10시 시작)
        hmu_start = datetime.combine(sched_date, datetime.min.time()) + timedelta(hours=random.randint(7, 10))
        shoot_start = hmu_start + timedelta(hours=1) # 1시간 뒤 촬영 시작
        shoot_end = shoot_start + timedelta(hours=random.choice([4, 8])) # 4시간(하프) 또는 8시간(풀) 촬영
        
        earn = random.choice([500, 1000, 1500, 2000])
        status = "completed" if sched_date < date.today() else "scheduled"
        
        s = {
            "model_id": model["id"],
            "title": f"Shoot for {random.choice(clients)}",
            "client_name": random.choice(clients),
            "schedule_date": sched_date.isoformat(),
            "hmu_start_time": hmu_start.isoformat() + "+09:00",
            "shoot_start_time": shoot_start.isoformat() + "+09:00",
            "shoot_end_time": shoot_end.isoformat() + "+09:00",
            "total_hours": float((shoot_end - hmu_start).seconds / 3600),
            "work_type": "half" if (shoot_end - shoot_start).seconds <= 4*3600 else "full",
            "earning_usd": earn,
            "status": status
        }
        schedules_data.append(s)
        
    # 스케줄 벌크 저장
    for i in range(0, len(schedules_data), 10):
        supabase.table("schedules").insert(schedules_data[i:i+10]).execute()
        
    print("Inserted 30 schedules.")
    print("DONE!")

if __name__ == "__main__":
    seed()
