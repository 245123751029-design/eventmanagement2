import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const BookingSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('checking'); // checking, success, failed
  const [attempts, setAttempts] = useState(0);
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (!sessionId) {
      navigate('/events');
      return;
    }
    checkPaymentStatus();
  }, [sessionId]);

  const checkPaymentStatus = async () => {
    if (attempts >= 5) {
      setStatus('failed');
      toast.error('Payment verification timed out');
      return;
    }

    try {
      const response = await axios.get(`${API}/bookings/payment-status/${sessionId}`, {
        withCredentials: true
      });

      if (response.data.payment_status === 'paid') {
        setStatus('success');
        toast.success('Payment successful!');
      } else if (response.data.status === 'expired') {
        setStatus('failed');
        toast.error('Payment session expired');
      } else {
        // Continue polling
        setAttempts(prev => prev + 1);
        setTimeout(checkPaymentStatus, 2000);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      setStatus('failed');
      toast.error('Failed to verify payment');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 text-center">
        {status === 'checking' && (
          <>
            <Loader2 className="w-16 h-16 text-blue-600 mx-auto mb-4 animate-spin" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Processing Payment</h2>
            <p className="text-gray-600">Please wait while we confirm your payment...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Booking Confirmed!</h2>
            <p className="text-gray-600 mb-6">Your payment was successful and your booking is confirmed.</p>
            <div className="space-y-3">
              <Button
                data-testid="view-bookings-btn"
                onClick={() => navigate('/my-bookings')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-full"
              >
                View My Bookings
              </Button>
              <Button
                onClick={() => navigate('/events')}
                variant="outline"
                className="w-full rounded-full"
              >
                Browse More Events
              </Button>
            </div>
          </>
        )}

        {status === 'failed' && (
          <>
            <XCircle className="w-16 h-16 text-red-600 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Failed</h2>
            <p className="text-gray-600 mb-6">There was an issue processing your payment. Please try again.</p>
            <Button
              onClick={() => navigate('/events')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-full"
            >
              Back to Events
            </Button>
          </>
        )}
      </Card>
    </div>
  );
};

export default BookingSuccess;
