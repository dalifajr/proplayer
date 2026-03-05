"""Test cam_filter in AutoPipeline."""
import sys
sys.path.insert(0, '.')
from lib.pipeline import AutoPipeline

class FakeSession:
    pass

p = AutoPipeline(FakeSession())

schools = [
    {'name': 'A', 'id': '1', 'camera_required': 'true'},
    {'name': 'B', 'id': '2', 'camera_required': 'false'},
    {'name': 'C', 'id': '3', 'camera_required': 'true'},
    {'name': 'D', 'id': '4', 'camera_required': 'false'},
    {'name': 'E', 'id': '5', 'camera_required': ''},
]

# Test None filter (all)
p.cam_filter = None
r = p._apply_cam_filter(schools)
names = [s['name'] for s in r]
print(f"Filter=None : {len(r)} schools -> {names}")
assert len(r) == 5, f"Expected 5, got {len(r)}"

# Test True filter (cam only) — should include A, C, E (not 'false')
p.cam_filter = True
r = p._apply_cam_filter(schools)
names = [s['name'] for s in r]
print(f"Filter=True : {len(r)} schools -> {names}")
assert set(names) == {'A', 'C', 'E'}, f"Expected A,C,E got {names}"

# Test False filter (upload only) — should include B, D
p.cam_filter = False
r = p._apply_cam_filter(schools)
names = [s['name'] for s in r]
print(f"Filter=False: {len(r)} schools -> {names}")
assert set(names) == {'B', 'D'}, f"Expected B,D got {names}"

# Test constructor with cam_filter
p2 = AutoPipeline(FakeSession(), cam_filter=True)
assert p2.cam_filter == True
p3 = AutoPipeline(FakeSession(), cam_filter=False)
assert p3.cam_filter == False
p4 = AutoPipeline(FakeSession())
assert p4.cam_filter is None

print()
print("All pipeline tests PASSED!")
