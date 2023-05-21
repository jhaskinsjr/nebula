#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>


#define STDOUT_FD	1
#define BUFLEN		(size_t)(1 << 10)


int	main(int, char **);
void do_cat(int, char *, size_t);


int
main(int argc, char ** argv)
{
	int fd = 0;
	char buf[BUFLEN];
	ssize_t n = 0;
	if (1 == argc) {
		do_cat(fd, buf, BUFLEN);
	} else {
		int x = 1;
		for (; x < argc; x += 1) {
			if (0 > (fd = open(argv[x], O_RDONLY))) continue;
			do_cat(fd, buf, BUFLEN);
			close(fd);
		}
	}
	return 0;
}

void
do_cat(int fd, char * buf, size_t buflen)
{
	ssize_t n = 0;
	while (n = read(fd, buf, buflen)) write(STDOUT_FD, buf, n);
}
