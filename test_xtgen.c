#include <stdio.h>

#include "xtgen.h"


int main(void)
{
	printf("clamped: %f\n", clamp(2.1, 2.5, 5.0));
	printf("scaled: %f\n", linear_scale(50.0, 0.0, 100.0, 0.0, 4000.0));

	printf("ease_in_sine: %f\n", ease_in_sine(50.0));
	printf("ease_out_sine: %f\n", ease_out_sine(50.0));
	printf("ease_inout_sine: %f\n", ease_inout_sine(50.0));

	printf("ease_in_quad: %f\n", ease_in_quad(50.0));
	printf("ease_out_quad: %f\n", ease_out_quad(50.0));
	printf("ease_inout_quad: %f\n", ease_inout_quad(50.0));

	printf("ease_in_cubic: %f\n", ease_in_cubic(50.0));
	printf("ease_out_cubic: %f\n", ease_out_cubic(50.0));
	printf("ease_inout_cubic: %f\n", ease_inout_cubic(50.0));

	printf("ease_in_quart: %f\n", ease_in_quart(50.0));
	printf("ease_out_quart: %f\n", ease_out_quart(50.0));
	printf("ease_inout_quart: %f\n", ease_inout_quart(50.0));

	printf("ease_in_quint: %f\n", ease_in_quint(50.0));
	printf("ease_out_quint: %f\n", ease_out_quint(50.0));
	printf("ease_inout_quint: %f\n", ease_inout_quint(50.0));

	printf("ease_in_expo: %f\n", ease_in_expo(50.0));
	printf("ease_out_expo: %f\n", ease_out_expo(50.0));
	printf("ease_inout_expo: %f\n", ease_inout_expo(50.0));

	printf("ease_in_circ: %f\n", ease_in_circ(50.0));
	printf("ease_out_circ: %f\n", ease_out_circ(50.0));
	printf("ease_inout_circ: %f\n", ease_inout_circ(50.0));

	printf("ease_in_back: %f\n", ease_in_back(50.0));
	printf("ease_out_back: %f\n", ease_out_back(50.0));
	printf("ease_inout_back: %f\n", ease_inout_back(50.0));

	printf("ease_in_elastic: %f\n", ease_in_elastic(50.0));
	printf("ease_out_elastic: %f\n", ease_out_elastic(50.0));
	printf("ease_inout_elastic: %f\n", ease_inout_elastic(50.0));

	printf("ease_in_bounce: %f\n", ease_in_bounce(50.0));
	printf("ease_out_bounce: %f\n", ease_out_bounce(50.0));
	printf("ease_inout_bounce: %f\n", ease_inout_bounce(50.0));
}
