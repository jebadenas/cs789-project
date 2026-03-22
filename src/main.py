from src.loader import load_all_sessions

if __name__ == "__main__":
    sessions = load_all_sessions("./data")

    for key, session in sorted(sessions.items()):
        year, sem, num = key
        print(f"\n{session.course} | {session.name}")
        for q_num, q in sorted(session.questions.items()):
            print(f"  Q{q_num} [{q.question_type:7s}]  {len(q.records):>4} records  —  {q.text[:60]}")
