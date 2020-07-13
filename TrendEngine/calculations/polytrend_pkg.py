import numpy as np
import numpy.linalg as lng
import numpy.polynomial.polynomial as poly
import scipy.stats as stats

#enter time series list with at least 4 records, eg. [0.1, 0.5, 0.3, 0.5]
time_series = []
#set desired statistical significance for the polynomial fit:
alpha = 0.05
Direction = 0
Slope = 0

def PolyTrend(Y, alpha):
    X = range(1, len(Y)+1)
 
    #define function to find p value:
    def Pvalue(coef, df, A, Aprim, pn):
        #generate square residual
        part_res = np.dot(A, pn)-Y
        residual = np.dot(part_res.transpose(), part_res)
        #generate variance-covariance matrix
        VC = lng.inv(np.dot(Aprim, A))*residual/df
        #compute variance of the first coefficient
        VC1 = np.sqrt(VC[0,0])
        #compute t-statistic
        statistic = coef/VC1
        #compute p value
        p = stats.t.sf(np.abs(statistic), df)*2
        return p
    
    def Plinear(X, Y):
        df1 = len(X)-2
        #generate Vandermonde matrix
        A1 = np.vander(X, 2)
        #generate transpose of the Vandermonde matrix
        Aprim1 = A1.transpose()
        p1 = np.dot(np.dot((lng.inv(np.dot(Aprim1, A1))), Aprim1), Y)
        coef1 = p1[0]
        Plin = Pvalue(coef1, df1, A1, Aprim1, p1)
        Slope = p1[0]
        Direction = np.sign(Slope)
        return Plin
    
    #degrees of freedom
    df3 = len(X)-4
    #generate Vandermonde matrix
    A3 = np.vander(X, 4)
    #generate transpose of the Vandermonde matrix
    Aprim3 = A3.transpose()
    #X=inv(A'*A)*A'*L - creating coefficients matrix:
    p3 = np.dot(np.dot((lng.inv(np.dot(Aprim3, A3))), Aprim3), Y)
    coef3 = p3[0]
    #compute p-value for cubic fit
    Pcubic = Pvalue(coef3, df3, A3, Aprim3, p3)
    #get roots of cubic polynomial
    coefs3 = ([p3[2], 2*p3[1], 3*p3[0]])
    roots3 = np.sort(poly.polyroots(coefs3))

    if (np.imag(roots3[0]) == 0 and np.imag(roots3[1])==0 and roots3[0] != roots3[1] and X[0] <= roots3[0] <= X[-1] and X[0] <= roots3[1] <= X[-1] and Pcubic < alpha):
        Plin = Plinear(X, Y)
        if (Plin < alpha):
            Trend_type = 3
            Significance = 1
            Poly_degree = 3
        else:
            Trend_type = -1
            Significance = -1
            Poly_degree = 3
            # return Trend_type, Significance, Poly_degree
    else:
        df2 = len(X)-3
        A2 = np.vander(X, 3)
        Aprim2 = A2.transpose()
        p2 = np.dot(np.dot((lng.inv(np.dot(Aprim2, A2))), Aprim2), Y)
        coef2 = p2[0]
        Pquadratic = Pvalue(coef2, df2, A2, Aprim2, p2)
        coefs2 = ([p2[1], 2*p2[0]])
        roots2 = np.sort(poly.polyroots(coefs2))
        
        if (X[0] <= roots2 <= X[-1] and Pquadratic < alpha):
            Plin = Plinear(X, Y)
            if Plin < alpha:
                Trend_type = 2
                Significance = 1
                Poly_degree = 2
            else:
                Trend_type = -1
                Significance = -1
                Poly_degree = 2
                # return Trend_type, Significance, Poly_degree
                
        else:
            Plin = Plinear(X, Y)
            if Plin < alpha:
                Trend_type = 1
                Significance = 1
                Poly_degree = 1
            else:
                Trend_type = 0
                Significance = -1
                Poly_degree = 0
            # return Trend_type, Significance, Poly_degree  
        # return Trend_type, Significance, Poly_degree
    result = {'trend_type': Trend_type, 'significance': Significance, 'polynomial_degree': Poly_degree, 'direction': Direction, 'slope': Slope} 
    return result