

.PHONEY: tests clean

all: tests


tests: test_pd test_mx

test_pd:
	gcc -o test_pd test_xtgen_pd.c

test_mx:
	gcc -o test_mx test_xtgen_mx.c

clean:
	@rm -f test_pd test_mx