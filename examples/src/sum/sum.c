// return the sum of the numbers on the command line

#include <stdio.h>
#include <stdlib.h>

int
main(int argc, char ** argv)
{
	int sum = 0;
	int x = 1;
	for (; x < argc; x += 1) sum += atoi(argv[x]);
	printf("%d\n", sum);
	return 0;
}
