def bucketize(sequence, max_size):
    buckets = []
    if not sequence:
        return buckets
    for i, each in enumerate(sequence):
        if not i:
            bucket = []
        elif not i % max_size:
            buckets.append(bucket)
            bucket = []
        bucket.append(each)
    if bucket:
        buckets.append(bucket)
    return buckets


def test_bucketize():
    buckets = bucketize(range(1, 12), 5)
    assert buckets == [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11]]

    buckets = bucketize(range(1, 11), 5)
    assert buckets == [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]


if __name__ == '__main__':
    test_bucketize()
