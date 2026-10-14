import json, sys, glob, collections
D = sys.argv[1]
memo = collections.Counter(); gold_non_memo = collections.Counter(); batch_memo = []
for f in sorted(glob.glob(f"{D}/answer-*.json")):
    i = int(f[-7:-5]); a = json.load(open(f))
    for c in a.get("data", []):
        if c.get("set_type") == "memorabilia":
            memo[(c["set"], c.get("set_name"), c.get("border_color"))] += 1
            if i <= 21: batch_memo.append((c["name"], c["set"]))
        if c.get("border_color") == "gold" and c.get("set_type") != "memorabilia":
            gold_non_memo[(c["set"], c.get("set_type"))] += 1
print("memorabilia sets seen:"); [print("  ", k, v) for k, v in sorted(memo.items())]
print("gold outside memorabilia:", dict(gold_non_memo))
print("batch printings in memorabilia:", batch_memo)
