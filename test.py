# coding=utf-8
l = [list(range(i, i + 4)) for i in range(10, 1, -1)]

def compare(item1,item2):
	return sum(item1) - sum(item2)

l = sorted(l, cmp=compare)
print l