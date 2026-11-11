import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from . import db, execute, one, now


def seed():
    if one("SELECT id FROM users WHERE email='admin@looplocal.test'"):
        return
    if one("SELECT id FROM users LIMIT 1"):
        raise ValueError(
            "Demo seeding requires an empty database; existing data was preserved."
        )
    accounts = [
        ("Amira Hassan", "resident@looplocal.test", "resident", "Petaling Jaya", ""),
        (
            "Daniel Tan",
            "fixer@looplocal.test",
            "fixer",
            "Petaling Jaya",
            "Electronics,Appliances,Bicycles",
        ),
        ("Community Admin", "admin@looplocal.test", "admin", "Petaling Jaya", ""),
        (
            "Mei Ling",
            "mei@looplocal.test",
            "fixer",
            "Subang Jaya",
            "Textiles,Furniture",
        ),
        ("Arjun Kumar", "arjun@looplocal.test", "resident", "Kuala Lumpur", ""),
        (
            "Sarah Lim",
            "sarah@looplocal.test",
            "fixer",
            "Kuala Lumpur",
            "Bicycles,Furniture",
        ),
    ]
    for name, email, role, area, skills in accounts:
        execute(
            "INSERT INTO users(name,email,password,role,area,skills) VALUES(?,?,?,?,?,?)",
            (name, email, generate_password_hash("LoopLocal2026!"), role, area, skills),
        )
    specs = [
        (
            1,
            None,
            "A little help for my desk lamp",
            "Electronics",
            "The LED desk lamp flickers after a few minutes. The cable is intact and there is no smell or visible damage.",
            1.2,
            "open",
        ),
        (
            5,
            None,
            "Give this reading chair another chapter",
            "Furniture",
            "The wooden chair has a loose leg joint. Looking for help to secure it rather than replace the whole chair.",
            6.5,
            "open",
        ),
        (
            1,
            2,
            "Weekend bicycle, ready to ride again",
            "Bicycles",
            "The rear brake cable was sticking and the gears needed adjustment.",
            12.0,
            "repaired",
        ),
        (
            5,
            4,
            "A second life for a favourite jacket",
            "Textiles",
            "A broken zipper and small tear on the left sleeve needed a careful repair.",
            0.8,
            "repaired",
        ),
        (
            1,
            2,
            "Table fan that deserves another summer",
            "Appliances",
            "The fan turns slowly on the lowest setting. No exposed cables or smoke. Please inspect before use.",
            3.2,
            "in_progress",
        ),
        (
            5,
            6,
            "Dining stool, back at the table",
            "Furniture",
            "A loose joint made this stool unstable. It needed a clean and re-glue.",
            4.5,
            "repaired",
        ),
    ]
    for owner, fixer, title, cat, desc, weight, status in specs:
        created = (datetime.now(timezone.utc) - timedelta(days=8)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        tid = execute(
            "INSERT INTO tickets(owner_id,fixer_id,title,category,description,area,status,safety,weight,public_code,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                owner,
                fixer,
                title,
                cat,
                desc,
                "Petaling Jaya" if owner == 1 else "Kuala Lumpur",
                status,
                "safe",
                weight,
                secrets.token_urlsafe(18),
                created,
                now(),
            ),
        ).lastrowid
        execute(
            "INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)",
            (tid, owner, "open", "Request created in demo community.", created),
        )
        if fixer:
            execute(
                "INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)",
                (tid, fixer, "assigned", "Volunteer accepted this repair.", created),
            )
            execute(
                "INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)",
                (
                    tid,
                    fixer,
                    "in_progress",
                    "Inspection and repair in progress.",
                    created,
                ),
            )
        if status == "repaired":
            execute(
                "INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)",
                (
                    tid,
                    fixer,
                    status,
                    "Repair completed; function and stability checked with the owner. Demo record.",
                    now(),
                ),
            )
    tools = [
        (
            "Precision screwdriver kit",
            "Electronics",
            "24 bits for small electronics. Use only on disconnected, low-voltage equipment.",
            "Petaling Jaya",
            2,
        ),
        (
            "Cordless drill & driver",
            "Furniture",
            "A compact drill, bit set and safety glasses. Hub safety briefing required.",
            "Petaling Jaya",
            1,
        ),
        (
            "Bicycle repair stand",
            "Bicycles",
            "Adjustable stand for cleaning, cable work and routine bicycle maintenance.",
            "Kuala Lumpur",
            1,
        ),
        (
            "Sewing machine",
            "Textiles",
            "Portable machine for mending everyday fabrics. Includes a starter thread kit.",
            "Subang Jaya",
            2,
        ),
        (
            "Digital multimeter",
            "Electronics",
            "For low-voltage checks only. Not for live mains work. Includes a user guide.",
            "Petaling Jaya",
            2,
        ),
        (
            "Woodwork clamp set",
            "Furniture",
            "Four quick-grip clamps for furniture re-gluing and small home repairs.",
            "Shah Alam",
            2,
        ),
    ]
    for item in tools:
        execute(
            "INSERT INTO tools(name,category,description,area,total) VALUES(?,?,?,?,?)",
            item,
        )
    for days, title, desc, location, capacity in [
        (
            3,
            "The Saturday Fix",
            "Bring one small item. Meet local repair volunteers, learn a practical skill and keep good things in use.",
            "PJ Community Hub · Section 14",
            16,
        ),
        (
            10,
            "Mend it, wear it",
            "A relaxed workshop on basic stitching, patching and zipper care. Bring a garment you love.",
            "Subang Community Studio",
            12,
        ),
        (
            17,
            "Bikes & better weekends",
            "Learn brake checks, puncture repair and simple bicycle maintenance with our volunteer team.",
            "KL Neighbourhood Workshop",
            10,
        ),
    ]:
        starts = (
            (datetime.now(timezone.utc) + timedelta(days=days))
            .replace(hour=2, minute=0, second=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        execute(
            "INSERT INTO clinics(title,description,location,starts,capacity,host_id) VALUES(?,?,?,?,?,3)",
            (title, desc, location, starts, capacity),
        )
    execute("INSERT INTO signups VALUES(1,1)")
    execute(
        "INSERT INTO notifications(user_id,body,link,created) VALUES(?,?,?,?)",
        (
            1,
            "Welcome to LoopLocal. Your next small repair can make a big difference.",
            "/dashboard",
            now(),
        ),
    )
