import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar, MapPin, Users, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Home = () => {
  const [events, setEvents] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchCategories();
    fetchEvents();
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [selectedCategory, searchQuery]);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const params = {};
      if (selectedCategory && selectedCategory !== 'all') params.category = selectedCategory;
      if (searchQuery) params.search = searchQuery;
      
      const response = await axios.get(`${API}/events`, { params });
      setEvents(response.data);
    } catch (error) {
      console.error('Error fetching events:', error);
      toast.error('Failed to load events');
    } finally {
      setLoading(false);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">Discover Amazing Events</h1>
          <p className="text-lg sm:text-xl text-blue-100 max-w-2xl">Find and book tickets for concerts, workshops, conferences, and more</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8 border border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                data-testid="search-events-input"
                type="text"
                placeholder="Search events..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-12 rounded-full border-gray-300"
              />
            </div>
            <Select value={selectedCategory || undefined} onValueChange={setSelectedCategory}>
              <SelectTrigger data-testid="category-filter-select" className="h-12 rounded-full">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.name}>{cat.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Events Grid */}
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="spinner"></div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-20">
            <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No events found</h3>
            <p className="text-gray-500">Try adjusting your filters or search query</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {events.map((event) => (
              <div
                key={event.id}
                data-testid={`event-card-${event.id}`}
                className="event-card bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl cursor-pointer border border-gray-100"
                onClick={() => navigate(`/events/${event.id}`)}
              >
                <div className="h-48 bg-gradient-to-br from-blue-400 to-purple-500 relative overflow-hidden">
                  {event.image_url ? (
                    <img src={event.image_url} alt={event.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Calendar className="w-16 h-16 text-white opacity-50" />
                    </div>
                  )}
                  <div className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-semibold text-gray-700">
                    {event.category}
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="text-xl font-bold text-gray-900 mb-2 line-clamp-2">{event.title}</h3>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">{event.description}</p>
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-blue-600" />
                      <span>{formatDate(event.date)}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-4 h-4 text-blue-600" />
                      <span className="line-clamp-1">{event.location}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-blue-600" />
                      <span>Capacity: {event.capacity}</span>
                    </div>
                  </div>
                  <Button data-testid={`view-details-btn-${event.id}`} className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full">
                    View Details
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
