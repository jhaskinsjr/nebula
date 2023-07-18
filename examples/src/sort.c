// return the count of comparison operations incident to sorting
// the numbers on the command line

#include <stdio.h>
#include <stdlib.h>

int
merge(int * buffer, unsigned int l, unsigned int c, unsigned int r)
{
	int retval = 0;
	unsigned int _d = 1 + c;
	if (buffer[c] <= buffer[_d]) goto done;
	while (l <= c && _d <= r) {
		if (buffer[l] <= buffer[_d]) {
			l += 1;
		} else {
			int value = buffer[_d];
			int index = _d;
			while (index != l) {
				buffer[index] = buffer[index - 1];
				index -= 1;
			}
			buffer[l] = value;
			l += 1;
			c += 1;
			_d += 1;
		}
		retval += 1;
	}
done:
	return retval;
}

int
mergesort(int * buffer, unsigned int l, unsigned int r)
{
	int retval = 0;
	if (l < r) {
		unsigned int _c = l + ((r - l) >> 1);
		retval += mergesort(buffer, l, _c);
		retval += mergesort(buffer, 1 + _c, r);
		retval += merge(buffer, l, _c, r);
	}
	return retval;
}

#define MAX_N	1 << 10

int
main(int argc, char ** argv)
{
	int swaps;
	int buffer[MAX_N]; // no more than MAX_N command-line parameters
	unsigned int x = 0;
	for (; x < argc - 1 && x < MAX_N; x += 1) buffer[x] = atoi(argv[1 + x]);
	swaps = (1 < argc) ? mergesort(buffer, 0, argc - 2) : 0;
	for (int y = 0; y < argc - 1; y += 1) printf("%d ", buffer[y]);
	puts("");
	return 0;
}
