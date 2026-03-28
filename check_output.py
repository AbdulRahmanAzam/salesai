import json, collections

d = json.load(open("output/prospect_queue.json"))
print(f"Total leads: {len(d)}")
print(f"With email: {sum(1 for x in d if x['contact']['email'])}")
print(f"With LinkedIn: {sum(1 for x in d if x['contact']['linkedin_url'])}")
print()
scores = [x["score"] for x in d]
print(f"Score range: {min(scores):.1f} - {max(scores):.1f}")
print(f"Avg score: {sum(scores)/len(scores):.1f}")
print()
companies = collections.Counter(x["contact"]["company_domain"] for x in d)
print("Leads per company:")
for co, cnt in companies.most_common():
    print(f"  {co}: {cnt}")

print("\nTop 10 leads:")
for i, x in enumerate(d[:10]):
    c = x["contact"]
    print(f"  {i+1}. {c['full_name']} - {c['title']}")
    print(f"     {c['company_name']} ({c['company_domain']}) | {c['email']}")
    print(f"     Score: {x['score']:.1f} | Source: {c['source']}")
