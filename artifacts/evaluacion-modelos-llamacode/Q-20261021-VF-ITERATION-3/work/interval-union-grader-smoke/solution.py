def covered_duration(intervals):
    pairs = list(intervals)
    if any(start > end for start, end in pairs):
        raise ValueError('reversed interval')
    pairs = sorted((start, end) for start, end in pairs if start < end)
    total = 0
    if not pairs:
        return total
    left, right = pairs[0]
    for start, end in pairs[1:]:
        if start > right:
            total += right - left
            left, right = start, end
        else:
            right = max(right, end)
    return total + right - left
