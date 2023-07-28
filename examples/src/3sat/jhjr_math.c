/* jhjr_math.c */


#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "jhjr_math.h"


static istack_t *		jhjr_stack=NULL;

static inline integer_t *	push(void);
static inline void		pop(void);


integer_t *
mkinteger(unsigned int nbits,int N)
{
	integer_t *	retval;
	unsigned int	nbytes;

	if (nbits<sizeof(int)*8)
		return NULL;
	retval=(integer_t *)malloc(sizeof(integer_t));
	assert(retval);
	retval->nbytes=nbytes=(nbits>>3)+((nbits & 0x7) ? 1 : 0);
#if 1
	retval->nbits=nbits;
#else
	retval->nbits=nbytes<<3;
#endif
	retval->data=(unsigned char *)malloc(nbytes);
	assert(retval->data);

	stinteger(retval,N);

	return retval;
}

void
rminteger(integer_t * s)
{
	if (s==NULL)
		return;

	if (s->data)
		free(s->data);
	free(s);
}

int
cpinteger(integer_t * d,integer_t * s)
{
	int	retval=JHJR_SUCCESS;

	assert(d);
	assert(s);
	if (d->nbytes>=s->nbytes) {
		unsigned int	offset=d->nbytes-s->nbytes;

		memcpy((void *)(d->data+offset),(void *)s->data,s->nbytes);
	} else {
		retval=JHJR_OVERFLOW;
	}

	return retval;
}

void
stinteger(integer_t * d,int N)
{
	assert(d);

	if (N & 0x80000000)
		memset((void *)d->data,0xff,d->nbytes);
	else
		memset((void *)d->data,0x00,d->nbytes);
#if	1
/* a "salute" to the x86 architecture's little-endianness... */
#if	1
	*((unsigned char *)(d->data+d->nbytes-1)-3)=(N & 0xff000000)>>24;
	*((unsigned char *)(d->data+d->nbytes-1)-2)=(N & 0x00ff0000)>>16;
	*((unsigned char *)(d->data+d->nbytes-1)-1)=(N & 0x0000ff00)>>8;
	*((unsigned char *)(d->data+d->nbytes-1)-0)=(N & 0x000000ff);
#else
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+0)=(N & 0xff000000)>>24;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+1)=(N & 0x00ff0000)>>16;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+2)=(N & 0x0000ff00)>>8;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+3)=(N & 0x000000ff);
#endif
#else
/* for big-endianness... */
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+3)=(N & 0xff000000)>>24;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+2)=(N & 0x00ff0000)>>16;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+1)=(N & 0x0000ff00)>>8;
	*((unsigned char *)((d->data+(d->nbytes-sizeof(int))))+0)=(N & 0x000000ff);
#endif
}

istack_t *
mkstack(unsigned int nbits,unsigned int nelem)
{
	unsigned int	i;
	istack_t *	retval;	

	if (nelem<=0)
		return NULL;

	retval=(istack_t *)malloc(sizeof(istack_t));
	assert(retval);
	retval->nelem=nelem;
	retval->nbits=nbits;
	retval->nbytes=(nbits>>3)+((nbits & 0x7) ? 1 : 0);
	retval->tosptr=0;
	retval->block=(integer_t **)malloc(sizeof(integer_t)*nelem);
	assert(retval->block);
	for(i=0;i<nelem;i++) {
		retval->block[i]=mkinteger(nbits,0);
		assert(retval->block[i]);
	}

	return retval;
}

void
rmstack(istack_t * S)
{
	unsigned int	i;

	if (S==NULL)
		return;
	for(i=0;i<S->nelem;i++) {
		if (S->block[i])
			rminteger(S->block[i]);
	}
	free(S);
}

void
ststack(istack_t * S)
{
	jhjr_stack=S;
}

static inline integer_t *
push(void)
{
	integer_t *	retval;

	assert(jhjr_stack);
	if (jhjr_stack->tosptr>=(jhjr_stack->nelem-1))
		return NULL;
	retval=jhjr_stack->block[jhjr_stack->tosptr];
	jhjr_stack->tosptr+=1;

	return retval;
}

static inline void
pop(void)
{
	assert(jhjr_stack);
	if (jhjr_stack->tosptr==0)
		return;
	jhjr_stack->tosptr-=1;
}

#define	MAX(a,b)	(((a) > (b)) ? (a) : (b))
#if 1
#define OPT_STACK
#endif

int
jhjr_add(integer_t * d,integer_t * s0,integer_t * s1)
{
	int		i,retval=JHJR_SUCCESS;
	integer_t *	tmp;
	integer_t *	src0;
	integer_t *	src1;
	unsigned int	intermediate;

	assert(d);
	assert(s0);
	assert(s1);

#if defined(OPT_STACK)
	if ((d==s0) || (d==s1)) {
		tmp=push();
		assert(tmp);
	} else {
		tmp=d;
	}
#else
	tmp=push();
	assert(tmp);
#endif
	stinteger(tmp,0);

#if defined(OPT_STACK)
	src1=s1;
	src0=s0;
#else
	src1=push();
	assert(src1);
	assert(cpinteger(src1,s1)==JHJR_SUCCESS);
	src0=push();
	assert(src0);
	assert(cpinteger(src0,s0)==JHJR_SUCCESS);
#endif

	intermediate=0;
	for (i=src0->nbytes-1;i>=0;i--) {
		intermediate=src1->data[i]+src0->data[i]+(intermediate>>8);
		tmp->data[i]=intermediate&0xff;
	}
	retval=((intermediate) ? JHJR_OVERFLOW : JHJR_SUCCESS);

#if !defined(OPT_STACK)
	pop(); /* src0 */
	pop(); /* src1 */
#endif
	if (d!=tmp) {
		cpinteger(d,tmp);
		pop(); /* tmp */
	}

	return retval;
}

#if 0
int
jhjr_sub(integer_t * d,integer_t * s0,integer_t * s1)
{
	int		retval=JHJR_SUCCESS;
	integer_t *	tmp;
	integer_t *	src0;
	integer_t *	src1;
	integer_t *	one;

	assert(d);
	assert(s0);
	assert(s1);

	tmp=push();
	assert(tmp);
	stinteger(tmp,0);

	src1=push();
	assert(src1);
	assert(cpinteger(src1,s1)==JHJR_SUCCESS);
	src0=push();
	assert(src0);
	assert(cpinteger(src0,s0)==JHJR_SUCCESS);
	one=push();
	assert(one);
	stinteger(one,1);

/* -N = not((unsigned)N) + 1... */
	jhjr_not(src1,src1);
	jhjr_add(src1,src1,one);
	retval=jhjr_add(tmp,src0,src1);

	if (retval==JHJR_SUCCESS || retval==JHJR_OVERFLOW) {
		cpinteger(d,tmp);
	}
	pop(); /* one */
	pop(); /* src0 */
	pop(); /* src1 */
	pop(); /* tmp */

	return retval;
}
#endif

int
jhjr_shift(integer_t * d,integer_t * s,unsigned int N,unsigned char op)
{
	int		i,retval=JHJR_SUCCESS;
	integer_t *	tmp;
	unsigned int	intermediate;
	unsigned int	offset;
	unsigned int	mask7;

	assert(d);
	assert(s);

#if defined(OPT_STACK)
	if (d==s) {
		tmp=push();
		assert(tmp);
	} else {
		tmp=d;
	}
#else
	tmp=push();
	assert(tmp);
#endif
	stinteger(tmp,0);

	offset=N>>3;
	mask7=N&0x7;
	intermediate=0;
	switch (op) {
	case JHJR_OP_SLL:
		if (N>=tmp->nbits)
			break;
		memcpy((void *)tmp->data,(void *)(s->data+offset),s->nbytes-offset);
		if (mask7==0)
			break;
		for(i=tmp->nbytes-1-offset;i>=0;i--) {
			intermediate=(tmp->data[i]<<mask7)|(intermediate>>8);
			tmp->data[i]=intermediate&0xff;
		}
		break;
	case JHJR_OP_SRA:
		if (tmp->data[0] & 0x80)
			stinteger(tmp,-1);
		intermediate=0xff<<(8-mask7);
	case JHJR_OP_SRL:
		if (N>=tmp->nbits)
			break;
		memcpy((void *)(tmp->data+offset),(void *)s->data,s->nbytes-offset);
		if (mask7==0)
			break;
		for(i=offset;i<tmp->nbytes;i++) {
			unsigned char	scratch;

			scratch=tmp->data[i];
			tmp->data[i]=(intermediate&0xff)|(scratch>>mask7);
			intermediate=scratch<<(8-mask7);
		}
		break;
	default:
		retval=JHJR_INVALIDOPERATOR;
		goto error;
	}

	if (d!=tmp) {
		cpinteger(d,tmp);
	}
error:
	if (d!=tmp) {
		pop(); /* tmp */
	}

	return retval;
}

int
jhjr_bitop(integer_t * d,integer_t * s0,integer_t * s1,unsigned char op)
{
	int		i,retval=JHJR_SUCCESS;
	integer_t *	tmp;

	assert(d);
	assert(s0);
	if (op!=JHJR_OP_NOT)
		assert(s1);
	else
		assert(s1==NULL);

#if defined(OPT_STACK)
	if ((d==s0) || (d==s1)) {
		tmp=push();
		assert(tmp);
	} else {
		tmp=d;
	}
#else
	tmp=push();
	assert(tmp);
#endif
	stinteger(tmp,0);

	if (op!=JHJR_OP_NOT && s0->nbytes!=s1->nbytes) {
		retval=JHJR_OPERANDMISMATCH;
		goto error;
	}

	switch (op) {
		case JHJR_OP_AND:
			for(i=s0->nbytes-1;i>=0;i--)
				tmp->data[i]=(s0->data[i] & s1->data[i]);
			break;
		case JHJR_OP_OR:
			for(i=s0->nbytes-1;i>=0;i--)
				tmp->data[i]=(s0->data[i] | s1->data[i]);
			break;
		case JHJR_OP_XOR:
			for(i=s0->nbytes-1;i>=0;i--)
				tmp->data[i]=(s0->data[i] ^ s1->data[i]);
			break;
		case JHJR_OP_NOT:
			for(i=s0->nbytes-1;i>=0;i--)
				tmp->data[i]=~(s0->data[i]);
			break;
		default:
			retval=JHJR_INVALIDOPERATOR;
			goto error;
	}

	if (d!=tmp) {
		cpinteger(d,tmp);
	}
error:
	if (d!=tmp) {
		pop(); /* tmp */
	}
	
	return retval;
}


int
jhjr_compar(integer_t * s0,integer_t * s1)
{
	int		i,retval;
	integer_t *	src0;
	integer_t *	src1;

	assert(s0);
	assert(s1);

#if defined(OPT_STACK)
	src1=s1;
	src0=s0;
#else
	src1=push();
	assert(src1);
	assert(cpinteger(src1,s1)==JHJR_SUCCESS);
	src0=push();
	assert(src0);
	assert(cpinteger(src0,s0)==JHJR_SUCCESS);
#endif

/* retval:
 *	-1 if s0 < s1
 *	 0 if s0 = s1
 *	 1 if s0 > s1
 */
	retval=0;
	for(i=0;retval==0 && i<src0->nbytes;i++) {
		if (src0->data[i]<src1->data[i]) {
			retval=-1;
		} else
		if (src0->data[i]>src1->data[i]) {
			retval=1;
		}
	}

#if !defined(OPT_STACK)
	pop(); /* src0 */
	pop(); /* src1 */
#endif

	return retval;
}

void
jhjr_dump(integer_t * s)
{
	int	i;

	printf("jhjr_dump(): s->nbits = %d\n",s->nbits);
	printf("jhjr_dump(): s->nbytes = %d\n",s->nbytes);
	for(i=0;i<s->nbytes;i++)
		printf("jhjr_dump(): s->data[%2d] = %02x\n",i,s->data[i]);
}

void
jhjr_puts(integer_t * s)
{
	int	i;

	for(i=0;i<s->nbytes;i++)
		printf("%02x",s->data[i]);
}
