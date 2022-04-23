int
atoi(const char * s)
{
	int retval = 0;
	int x = 0;
	while (s[x] >= 48 && s[x] <= 57) {
		retval *= 10;
		retval += s[x] - 48;
		x += 1;
	}
	return retval;
}