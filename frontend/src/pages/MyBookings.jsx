import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar, MapPin, Ticket, CheckCircle, Clock, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import QRCode from 'react-qr-code';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [qrCodeUrl, setQrCodeUrl] = useState(null);

  useEffect(() => {
    fetchMyBookings();
  }, []);

  const fetchMyBookings = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/bookings/my-bookings/list`, {
        withCredentials: true
      });
      setBookings(response.data);
    } catch (error) {
      console.error('Error fetching bookings:', error);
      toast.error('Failed to load your bookings');
    } finally {
      setLoading(false);
    }
  };

  const viewQRCode = async (booking) => {
    try {
      const response = await axios.get(`${API}/bookings/${booking.id}/qr`, {
        withCredentials: true,
        responseType: 'blob'
      });
      const url = URL.createObjectURL(response.data);
      setQrCodeUrl(url);
      setSelectedBooking(booking);
    } catch (error) {
      console.error('Error fetching QR code:', error);
      toast.error('Failed to load QR code');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'confirmed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-600" />;
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-8">My Bookings</h1>

        {bookings.length === 0 ? (
          <Card className="p-12 text-center">
            <Ticket className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No bookings yet</h3>
            <p className="text-gray-500">Your event bookings will appear here</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {bookings.map((booking) => (
              <Card key={booking.id} data-testid={`booking-card-${booking.id}`} className="overflow-hidden hover:shadow-lg">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                    <div className="flex-1 mb-4 md:mb-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-xl font-bold text-gray-900">{booking.event_title}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1 ${getStatusColor(booking.status)}`}>
                          {getStatusIcon(booking.status)}
                          <span className="capitalize">{booking.status}</span>
                        </span>
                      </div>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-4 h-4 text-blue-600" />
                          <span>{formatDate(booking.event_date)}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <MapPin className="w-4 h-4 text-blue-600" />
                          <span>{booking.event_location}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Ticket className="w-4 h-4 text-blue-600" />
                          <span>{booking.ticket_type_name} × {booking.quantity}</span>
                        </div>
                      </div>
                      <div className="mt-3">
                        <span className="text-lg font-bold text-gray-900">
                          Total: ${booking.total_price.toFixed(2)}
                        </span>
                      </div>
                    </div>
                    {booking.status === 'confirmed' && (
                      <Button
                        data-testid={`view-qr-btn-${booking.id}`}
                        onClick={() => viewQRCode(booking)}
                        className="bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center space-x-2"
                      >
                        <Ticket className="w-4 h-4" />
                        <span>View QR Code</span>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* QR Code Dialog */}
      <Dialog open={!!selectedBooking} onOpenChange={() => {
        setSelectedBooking(null);
        if (qrCodeUrl) {
          URL.revokeObjectURL(qrCodeUrl);
          setQrCodeUrl(null);
        }
      }}>
        <DialogContent data-testid="qr-code-dialog" className="max-w-md">
          <DialogHeader>
            <DialogTitle>Ticket QR Code</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedBooking && (
              <>
                <div className="text-center">
                  <h3 className="font-bold text-lg mb-1">{selectedBooking.event_title}</h3>
                  <p className="text-sm text-gray-600">{selectedBooking.ticket_type_name} × {selectedBooking.quantity}</p>
                </div>
                {qrCodeUrl && (
                  <div className="flex justify-center p-6 bg-white">
                    <img src={qrCodeUrl} alt="Ticket QR Code" className="w-64 h-64" />
                  </div>
                )}
                <p className="text-xs text-center text-gray-500">
                  Show this QR code at the event entrance
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyBookings;
