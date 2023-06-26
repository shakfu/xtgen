#include <math.h>

#define PI 3.1415926535
#define HALF_PI 1.5707963


/*
 * General helper functions for xtgen templates
 */

float clamp(float value, float smallest, float largest)
{
    return fmax(smallest, fmin(value, largest));
}

float linear_scale(float x, float from_min, float from_max, float to_min, float to_max)
{
    return ((to_max - to_min) * (x - from_min) / (from_max - from_min)) + to_min;
}

// add easing functions... from https://github.com/nicolausYes/easing-functions


double ease_in_linear(double t, double b, double c, double d)
{ 
	return (c * t / d + b);
}

double ease_out_linear(double t, double b, double c, double d)
{ 
	return (c * t / d + b);
}

double ease_inout_linear(double t, double b, double c, double d)
{ 
	return (c * t / d + b);
}

double ease_in_sine(double t)
{
	return sin(HALF_PI * t);
}

double ease_out_sine(double t)
{
	return 1 + sin(HALF_PI * (--t));
}

double ease_inout_sine(double t)
{
    return 0.5 * (1 + sin(PI * (t - 0.5)));
}

double ease_in_quad(double t)
{
	return t * t;
}

double ease_out_quad(double t)
{
	return t * (2 - t);
}

double ease_inout_quad(double t)
{
    return t < 0.5 ? 2 * t * t : t * (4 - 2 * t) - 1;
}

double ease_in_cubic(double t)
{ 
	return t * t * t;
}

double ease_out_cubic(double t)
{
	double t1 = t - 1.0;
	return 1 + t1 * t * t;
}

double ease_inout_cubic(double t)
{
	double t1 = t - 1.0;
    return t < 0.5 ? 4 * t * t * t : 1 + t1 * (2 * t1) * (2 * t);
}

double ease_in_quart(double t)
{
    t *= t;
    return t * t;
}

double ease_out_quart(double t)
{
	double t1 = t - 1.0;
    t = t1 * t;
    return 1 - t * t;
}

double ease_inout_quart(double t)
{
    if (t < 0.5) {
        t *= t;
        return 8 * t * t;
    } else {
    	double t1 = t - 1.0;
        t = t1 * t;
        return 1 - 8 * t * t;
    }
}

double ease_in_quint(double t)
{
    double t2 = t * t;
    return t * t2 * t2;
}

double ease_out_quint(double t)
{
	double t1 = t - 1.0;
    double t2 = t1 * t;
    return 1 + t * t2 * t2;
}

double ease_inout_quint(double t)
{
    double t2;
    if (t < 0.5) {
        t2 = t * t;
        return 16 * t * t2 * t2;
    } else {
    	double t1 = t - 1.0;
        t2 = t1 * t;
        return 1 + 16 * t * t2 * t2;
    }
}

double ease_in_expo(double t)
{ 
	return (pow(2, 8 * t) - 1) / 255;
}

double ease_out_expo(double t)
{ 
	return 1 - pow(2, -8 * t);
}

double ease_inout_expo(double t)
{
    if (t < 0.5) {
        return (pow(2, 16 * t) - 1) / 510;
    } else {
        return 1 - 0.5 * pow(2, -16 * (t - 0.5));
    }
}

double ease_in_circ(double t)
{
	return 1 - sqrt(1 - t);
}

double ease_out_circ(double t)
{
	return sqrt(t);
}

double ease_inout_circ(double t)
{
    if (t < 0.5) {
        return (1 - sqrt(1 - 2 * t)) * 0.5;
    } else {
        return (1 + sqrt(2 * t - 1)) * 0.5;
    }
}

double ease_in_back(double t)
{ 
	return t * t * (2.70158 * t - 1.70158);
}

double ease_out_back(double t)
{ 
	double t1 = t - 1.0;
	return 1 + t1 * t * (2.70158 * t + 1.70158);
}

double ease_inout_back(double t)
{
    if (t < 0.5) {
        return t * t * (7 * t - 2.5) * 2;
    } else {
    	double t1 = t - 1.0;
        return 1 + t1 * t * 2 * (7 * t + 2.5);
    }
}

double ease_in_elastic(double t)
{
    double t2 = t * t;
    return t2 * t2 * sin(t * PI * 4.5);
}

double ease_out_elastic(double t)
{
    double t2 = (t - 1) * (t - 1);
    return 1 - t2 * t2 * cos(t * PI * 4.5);
}

double ease_inout_elastic(double t)
{
    double t2;
    if (t < 0.45) {
        t2 = t * t;
        return 8 * t2 * t2 * sin(t * PI * 9);
    } else if (t < 0.55) {
        return 0.5 + 0.75 * sin(t * PI * 4);
    } else {
        t2 = (t - 1) * (t - 1);
        return 1 - 8 * t2 * t2 * sin(t * PI * 9);
    }
}

double ease_in_bounce(double t)
{
    return pow(2, 6 * (t - 1)) * fabs(sin(t * PI * 3.5));
}

double ease_out_bounce(double t)
{
    return 1 - pow(2, -6 * t) * fabs(cos(t * PI * 3.5));
}

double ease_inout_bounce(double t)
{
    if (t < 0.5) {
        return 8 * pow(2, 8 * (t - 1)) * fabs(sin(t * PI * 7));
    } else {
        return 1 - 8 * pow(2, -8 * t) * fabs(sin(t * PI * 7));
    }
}