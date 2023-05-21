#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>


#define STDOUT_FD	1
#define BUFLEN		(1 << 10)


int	main(int, char **);


int
main(int argc, char ** argv)
{
	int fd = 0;
	char buf[BUFLEN];
	ssize_t n = 0;
	if (2 == argc) fd = open(argv[1], O_RDONLY);
	if (0 > fd) return -1;
	while (n = read(fd, buf, BUFLEN)) write(STDOUT_FD, buf, n);
	close(fd);
	return 0;
}
