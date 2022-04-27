int
atoi(const char * s)
{
	int retval = 0;
	int x = 0;
	while (s[x] >= '0' && s[x] <= '9') {
		retval *= 10;
		retval += s[x] - '0';
		x += 1;
	}
	return retval;
}